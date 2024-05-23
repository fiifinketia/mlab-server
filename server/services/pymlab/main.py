import os
import shutil
import subprocess
import uuid


NATIVE_PACKAGES = ['test', 'train']

def load_pkg(
    p_type: str,
    name: str,
    to: str,
    code: str | None,
):
    if p_type == 'native':
        load_native_pkg(name, to)
        return
    raise Exception("Only native types allowed now")

def load_native_pkg(name: str, to: str):
    if NATIVE_PACKAGES.index(name) == -1:
        raise Exception("Selected package does not exist")
    # find the native package which is a file `name.py` in current directory
    # then create a copy of the file in the to directory
    copy_native_package(name, to)

def find_native_package(name: str) -> str:
  current_directory = os.getcwd()
  for file_name in os.listdir(current_directory):
    if file_name == f"{name}.py":
      return os.path.join(current_directory, file_name)
  raise Exception("Native package not found")

def copy_native_package(name: str, to: str):
  package_path = find_native_package(name)
  shutil.copy(package_path, to)

def run_native_pkg(
    name: str,
    at: str,
    result_id: uuid.UUID,
    api_url: str,
    trained_model: str=None,
) -> subprocess.CompletedProcess[bytes]:
    """Run a script in a virtual environment using ProcessPoolExecutor"""
    # Activate the virtual environment
    venv_path = f"{at}/venv"
    activate_venv = f"source {venv_path}/bin/activate"

    # Prepare the command to run the script with arguments
    script_path = f"{at}/{name}.py"
    config_path = f"{at}/config.txt"
    run_script = f"python {script_path} --config {config_path} --result_id {result_id} --trained_model {trained_model} --api_url {api_url}"

    # Combine the commands
    command = f"{activate_venv} && {run_script}"

    # Run the command
    return subprocess.run(command, shell=True, executable="/bin/bash", check=True)