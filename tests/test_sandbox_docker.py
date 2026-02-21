import pytest
from unittest.mock import MagicMock, patch
from app.sandbox.docker import DockerSandbox

@patch("app.sandbox.docker.docker")
def test_docker_sandbox_start(mock_docker):
    mock_client = MagicMock()
    mock_docker.from_env.return_value = mock_client
    mock_container = MagicMock()
    mock_client.containers.run.return_value = mock_container
    mock_container.id = "test_container_id"

    sandbox = DockerSandbox()
    sandbox.start()

    mock_client.containers.run.assert_called_once()
    assert sandbox.container_id == "test_container_id"

@patch("app.sandbox.docker.docker")
def test_docker_sandbox_exec(mock_docker):
    mock_client = MagicMock()
    mock_docker.from_env.return_value = mock_client
    mock_container = MagicMock()
    mock_client.containers.run.return_value = mock_container

    # Mock exec_run result. docker-py returns (exit_code, output) or (exit_code, (stdout, stderr)) if demux=True
    # In my implementation I used demux=True
    mock_exec_result = MagicMock()
    mock_exec_result.exit_code = 0
    mock_exec_result.output = (b"hello", b"")
    mock_container.exec_run.return_value = mock_exec_result

    sandbox = DockerSandbox()
    sandbox.start()

    code, out = sandbox.exec_run("echo hello")

    assert code == 0
    assert "hello" in out
    mock_container.exec_run.assert_called_with("echo hello", workdir="/workspace", demux=True)
