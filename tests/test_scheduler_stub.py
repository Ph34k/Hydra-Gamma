from app.agent.manus import Manus
from app.utils.scheduler import SchedulerService

# Assuming Manus agent and other dependencies are correctly set up.

if __name__ == "__main__":
    # Example to test scheduler integration (not full service deployment)
    try:
        scheduler = SchedulerService()
        print("Scheduler initialized.")
        # In a real app, this would be run as part of the startup
    except Exception as e:
        print(f"Failed to init scheduler: {e}")
