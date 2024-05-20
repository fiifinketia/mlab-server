import subprocess

from server.settings import settings


def generate_key_pair(user_id: str) -> list[bytes]:
  # Generate key_pair at settings.ssh_key_path
    ssh_keygen_command = f"ssh-keygen -t rsa -b 4096 -f {settings.ssh_key_path}/id_{user_id} -q -N ''"
    ssh_keygen = subprocess.Popen(
        ssh_keygen_command,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        shell=True
      )

    if ssh_keygen.stdout is None:
        raise Exception("Error generating key pair")
    
    print(ssh_keygen.stdout.readlines())
    
    return ssh_keygen.stdout.readlines()


def add_public_key(public_key: str) -> None:
    # Add publbic key to authorized_keys in settings.ssh_key_path
    authorized_keys_path = f"{settings.ssh_key_path}/authorized_keys"
    with open(authorized_keys_path, "a") as f:
        f.write(public_key + "\n")

def remove_public_key(public_key: str) -> None:
    # Remove public key from authorized_keys in settings.ssh_key_path
    authorized_keys_path = f"{settings.ssh_key_path}/authorized_keys"
    with open(authorized_keys_path, "r") as f:
        lines = f.readlines()
    with open(authorized_keys_path, "w") as f:
        for line in lines:
            if line.strip("\n") != public_key:
                f.write(line)