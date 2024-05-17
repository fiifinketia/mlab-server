import subprocess

from server.settings import settings


def generate_key_pair(user_id: str) -> list[bytes]:
  # SSH to server and generate a key pair
  # Return the key pair
    ssh_connect_command = f"ssh -i {settings.ssh_key_path} disal@appatechlab.com -oPort=6000"
    ssh_command = f"ssh-keygen -t rsa -b 4096 -f /root/.ssh/id_{user_id} -N ''"
    ssh_command += f" && cat /root/.ssh/id_{user_id}.pub"
    ssh_command += f" && cat /root/.ssh/id_{user_id}"

    ssh = subprocess.Popen(
        ssh_connect_command,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        shell=True
      )
    if ssh.stderr:
        print(ssh.stderr.readlines())
        # raise Exception("Error connecting to server")
    
    if ssh.stdin is None:
        raise Exception("Error connecting to server")
    
    ssh.stdin.write(ssh_command.encode())
    ssh.stdin.close()
    if ssh.stdout is None:
        raise Exception("Error connecting to server")
    result = ssh.stdout.readlines()
    print(result)
    return result


def remove_key_pair(user_id: str) -> None:
  # SSH to server and remove the key pair
    ssh_connect_command = f"ssh -i {settings.ssh_key_path} disal@appatechlab.com -oPort=6000"
    ssh_command = f"rm /root/.ssh/id_{user_id}"
    ssh_command += f" && rm /root/.ssh/id_{user_id}.pub"

    ssh = subprocess.Popen(
        ssh_connect_command,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        shell=True
      )
    if ssh.stderr:
        print(ssh.stderr.readlines())
        raise Exception("Error connecting to server")
    
    if ssh.stdin is None:
        raise Exception("Error connecting to server")
    
    ssh.stdin.write(ssh_command.encode())
    ssh.stdin.close()
    if ssh.stdout is None:
        raise Exception("Error connecting to server")
