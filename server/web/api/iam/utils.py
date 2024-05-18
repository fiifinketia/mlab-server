import subprocess

from server.settings import settings


def generate_key_pair(user_id: str) -> list[bytes]:
  # SSH to server and generate a key pair
  # Return the key pair
    ssh_connect_command = f"ssh -i {settings.ssh_key_path} disal@appatechlab.com -oPort=6000 -tt"
    ssh_command = f"ssh-keygen -t rsa -b 4096 -f /root/.ssh/id_{user_id} -N ''"
    ssh_command += f" && cat /root/.ssh/id_{user_id}.pub"
    ssh_command += f" && cat /root/.ssh/id_{user_id}"
    # get ip
    ip = subprocess.run(
        "ipconfig eth0 | grep 'inet ' | awk '{print $2}' | cut -d: -f2",
        stdout=subprocess.PIPE,
        shell=True
      ).stdout.decode().strip()
    print(ip)
    # check host key
    knowhost = subprocess.Popen(
        "ssh-keygen -R appatechlab.com",
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        shell=True
      )
    if knowhost.stderr:
        print(knowhost.stderr.readlines())
        # raise Exception("Error connecting to server")
    
    # if knowhost.stdin is None:
    #     raise Exception("Error connecting to server")
    
    if knowhost.stdout is None:
        raise Exception("Error connecting to server")

    print(knowhost.stdout.readlines())

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
