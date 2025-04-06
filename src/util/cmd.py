import subprocess
from lib.logger import Logger


class Cmd:

    @staticmethod
    def run_at_command(command):
        """
        Runs an AT command on the modem using gl_modem
        """

        try:
            result = subprocess.run(['gl_modem', 'AT', command],
                                    capture_output=True,
                                    text=True,
                                    check=True)
            return result.stdout
        except subprocess.CalledProcessError as e:
            Logger.error(f"Error running AT command: {e}")
            return ""
