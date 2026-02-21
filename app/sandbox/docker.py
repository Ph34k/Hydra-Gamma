import docker
import tarfile
import io
import time
import os
import shutil
from typing import Dict, Optional, Tuple, Any
from uuid import UUID

from app.logger import logger
from app.sandbox.monitor import ResourceMonitor

class DockerSandbox:
    """
    A secure, isolated execution environment based on Docker containers.
    Ref: Chapter 16 of the Technical Bible.
    """

    def __init__(self, image: str = "python:3.12-slim", timeout: int = 3600, memory_limit: str = "512m"):
        self.client = docker.from_env()
        self.image = image
        self.container = None
        self.container_id = None
        self.timeout = timeout
        self.memory_limit = memory_limit
        self.monitor = None
        self.working_dir = "/workspace"

    def start(self):
        """Start the sandbox container."""
        try:
            logger.info(f"Starting Docker sandbox with image {self.image}...")
            self.container = self.client.containers.run(
                self.image,
                command="tail -f /dev/null", # Keep alive
                detach=True,
                mem_limit=self.memory_limit,
                working_dir=self.working_dir,
                pids_limit=512, # Chapter 17
                cpu_quota=50000, # 50% CPU
                # network_mode="none", # Strict isolation by default, but we might need net for tools
                volumes={
                     # We might want to mount a volume for persistence if needed,
                     # but ephemeral is better for security (Chapter 16.5)
                }
            )
            self.container_id = self.container.id
            self.monitor = ResourceMonitor(
                UUID(int=0),
                limits={"timeout": self.timeout},
                container_id=self.container_id
            )

            # Setup workspace
            self.exec_run(f"mkdir -p {self.working_dir}")

            logger.info(f"Sandbox started: {self.container_id[:12]}")
        except Exception as e:
            logger.error(f"Failed to start sandbox: {e}")
            raise

    def stop(self):
        """Stop and remove the sandbox container."""
        if self.container:
            try:
                self.container.stop(timeout=1)
                self.container.remove(force=True)
                logger.info(f"Sandbox stopped: {self.container_id[:12]}")
            except Exception as e:
                logger.error(f"Failed to stop sandbox: {e}")
            finally:
                self.container = None
                self.container_id = None

    def exec_run(self, cmd: str, workdir: Optional[str] = None, timeout: Optional[int] = None) -> Tuple[int, str]:
        """
        Execute a command inside the container.
        Returns: (exit_code, output)
        """
        if not self.container:
            raise RuntimeError("Sandbox not started")

        try:
            # We use a simple exec_run. For complex interactions (like shell session),
            # we might need a persistent process (like 'sh') and interact via socket.
            # But exec_run is sufficient for 'python_execute' and simple shell commands.

            # Note: docker-py exec_run returns (exit_code, output_bytes)
            # It blocks until completion unless detach=True.

            # To handle timeout, we might need a wrapper or use detach=True and poll.
            # For simplicity, we assume synchronous execution for now.

            exec_result = self.container.exec_run(
                cmd,
                workdir=workdir or self.working_dir,
                demux=True # Separate stdout/stderr
            )
            exit_code = exec_result.exit_code
            stdout, stderr = exec_result.output

            output = ""
            if stdout:
                output += stdout.decode('utf-8', errors='replace')
            if stderr:
                output += f"\nSTDERR: {stderr.decode('utf-8', errors='replace')}"

            return exit_code, output
        except Exception as e:
            return -1, str(e)

    def read_file(self, filepath: str) -> str:
        """Read a file from the container."""
        if not self.container:
            raise RuntimeError("Sandbox not started")

        try:
            # get_archive returns a tuple (generator, stat)
            bits, stat = self.container.get_archive(filepath)

            file_obj = io.BytesIO()
            for chunk in bits:
                file_obj.write(chunk)
            file_obj.seek(0)

            with tarfile.open(fileobj=file_obj) as tar:
                # The tar contains the file (or directory).
                # If filepath is absolute, it might be tricky.
                # Assuming single file.
                member = tar.next()
                f = tar.extractfile(member)
                if f:
                    return f.read().decode('utf-8', errors='replace')
            return ""
        except docker.errors.NotFound:
            raise FileNotFoundError(f"File {filepath} not found in sandbox")
        except Exception as e:
            raise RuntimeError(f"Failed to read file: {e}")

    def write_file(self, filepath: str, content: str):
        """Write a file to the container."""
        if not self.container:
            raise RuntimeError("Sandbox not started")

        try:
            # Create a tar archive in memory
            file_obj = io.BytesIO()
            with tarfile.open(fileobj=file_obj, mode='w') as tar:
                data = content.encode('utf-8')
                tar_info = tarfile.TarInfo(name=os.path.basename(filepath))
                tar_info.size = len(data)
                tar_info.mtime = time.time()
                tar.addfile(tar_info, io.BytesIO(data))

            file_obj.seek(0)

            # Copy archive to container
            # We put it in the dirname of filepath
            parent_dir = os.path.dirname(filepath) or "."
            self.container.put_archive(parent_dir, file_obj)
        except Exception as e:
            raise RuntimeError(f"Failed to write file: {e}")

    def __del__(self):
        if self.container:
            try:
                self.container.remove(force=True)
            except:
                pass
