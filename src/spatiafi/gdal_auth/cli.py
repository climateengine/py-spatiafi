import sys
import tempfile
from pathlib import Path
from typing import Dict

import click

from spatiafi.gdal_auth.gdal_auth import get_gdal_env_vars

GDAL_CLI_TOOLS = [
    "gdalinfo",
    "gdal_translate",
    "gdalwarp",
    "gdalbuildvrt",
    "gdaladdo",
    "gdal_grid",
    "gdallocationinfo",
    "gdalmanage",
    "gdalsrsinfo",
    "gdaltindex",
    "gdaltransform",
    "gdal_contour",
    "gdal_rasterize",
    "gdal_edit",
    "gdal_merge",
    "gdal_pansharpen",
    "gdal_polygonize",
    "gdal_proximity",
    "gdal_retile",
    "gdal_sieve",
    "gdalcompare",
    "gdalident",
    "gdallocationinfo",
    "gdalmanage",
]


def set_env_source_file(env: Dict[str, str]):
    """Sets environment variables using a source file"""
    # create a temporary file to store the env vars
    env_file = Path(tempfile.gettempdir()) / "gdal_auth.env"

    with env_file.open("w") as f:
        for k, v in env.items():
            f.write(f"export {k}={v}\n")

    # Instructions for setting the env vars
    print("Env vars saved to: ", env_file)
    print("Run the following command in your command line to set the env vars:\n")
    print(f"source {env_file}")
    print("")


def set_env_one_line_command(env: Dict[str, str], pre=False):
    """Sets environment variables using a one line command"""
    if not pre:
        print("Run the following command in your command line to set the env vars:\n")
    print("export " + " ".join([f"{k}={v}" for k, v in env.items()]), ";")


def print_alias_instructions(project=None):
    """Prints instructions for setting up an alias"""
    # set alias file to ~/.gdal_aliases
    alias_file = Path.home() / ".gdal_aliases"
    this_file = Path(__file__).absolute()
    py_exe = Path(sys.executable).absolute() if sys.executable else "python"
    project_arg = f"--project {project}" if project else ""
    bash_func = (
        f'gdal_auth_hook() {{ eval "$({py_exe} {this_file} --pre {project_arg})"; }}'
    )

    with open(alias_file, "w") as f:
        f.write(bash_func + "\n")
        f.write("export -f gdal_auth\n")
        for gdal_cmd in GDAL_CLI_TOOLS:
            alias_cmd = f'alias {gdal_cmd}="gdal_auth_hook && {gdal_cmd}"'
            f.write(alias_cmd + "\n")

    print("Run the following command in your command line to set the aliases:\n")
    print(f"source {alias_file}")
    print("")
    print(
        "After the aliases are set, you can use GDAL commands as normal, e.g. `gdalinfo gs://my-bucket/my-file.tif`"
    )
    print("and authentication will be handled automatically")
    print("")
    print(
        f"You can also add 'source {alias_file}' line to your ~/.bashrc file to load the aliases on startup"
    )


@click.command()
@click.option("-f", "--file", is_flag=True, help="Create an env file")
@click.option("-l", "--line", is_flag=True, help="Print a one line command")
@click.option("-a", "--alias", is_flag=True, help="Print alias instructions")
@click.option(
    "-p",
    "--project",
    default=None,
    help="GCP project ID to use for billing (default: from ADC)",
)
@click.option(
    "--pre", is_flag=True, help="Run as a pre-command to a GDAL/rio (used by aliases)"
)
def cli(file, line, alias, project, pre):
    """Set environment variables needed for GDAL to authenticate to Google Cloud"""
    env = get_gdal_env_vars(project=project)
    if file:
        set_env_source_file(env)
    elif line:
        set_env_one_line_command(env)
    elif alias:
        print_alias_instructions(project=project)
    elif pre:
        set_env_one_line_command(env, pre=True)
    else:
        print("Set the following environment variables:\n")
        for k, v in env.items():
            print(f"{k}={v}")


if __name__ == "__main__":
    cli()
