#!/usr/bin/env /usr/bin/python3

# Runs-with python3
# 
# Dependencies:
#   * GitPython
#

# === MODIFY these if you need to === #
INTERPRETER: str = "/usr/bin/python3"
GIT_COMMAND: str = "/usr/local/bin/git" # needs absolute path
VSCODE_COMMAND: str = "/usr/local/bin/code" # needs absolute path
LOG_FILE_NAME: str = "" # empty string = disabled

# Format:
#   [ ] list of users with configuration
#   [0] = GitHub username
#   [1] = GitHub API_TOKEN
#   [2] = Rootfolder for repositories of that user (needs absolute path)
USER_DATA = [
    ("user", "api-key", "path-to-users-repositories"),
]
# === DO NOT modify below this line for configuration (unless you know what you do) === #

import base64
import os
import sys
import datetime
import git
from typing import Any, Dict, Iterator, List, Tuple

import requests

class CMD:
    @classmethod
    def prefix(cls, level: int) -> str:
        return "--" * level

    @classmethod
    def build_bash_command(cls, cmds: List[str]) -> str:
        return " && ".join(cmds)
    
    @classmethod
    def quote(cls, string: str) -> str:
        return "\"" + string + "\""

    @classmethod
    def build_command(cls, level: int, caption: str, *, command: str = "", command_param: str = "",
        terminal: bool = False, refresh: bool = False, color: str = "white", **kwargs: Dict[Any, Any]) -> str:
        cmd = " ".join([cls.prefix(level), caption])
        params = []
        if color != "white":
            params.append("color="+color)
        if refresh:
            params.append("refresh=" + str(refresh).lower())
        if any(command):
            params.append("terminal=" + str(terminal).lower())
            command_param_encoded = base64.b64encode(command_param.encode("ascii")).decode("ascii")
            params.append("bash=" + INTERPRETER + " param1=" + __file__ + " param2=" + command + " param3=" + command_param_encoded)

        for arg, val in kwargs.items():
            params.append(arg + "=" + str(val))
        if any(params):
            cmd += " | " + " ".join(params)
        return cmd

    @classmethod
    def hbar(cls, level: int) -> str:
        return cls.prefix(level) + "---"

class Wrap:
    @classmethod
    def git(cls, args: str) -> str:
        return GIT_COMMAND + " " + args

    @classmethod
    def vscode(cls, args: str) -> str:
        return VSCODE_COMMAND + " " + args

class WorkingDir:
    def __init__(self, directory: str):
        self.directory: str = directory

    def ensure(self):
        if not os.path.isdir(self.directory):
            os.mkdir(self.directory)

    def log_file(self) -> str:
        return self.directory + "/" + LOG_FILE_NAME

    def log(self, v: Any):
        if LOG_FILE_NAME == "":
            return
        msg = "{t} | {v}\n".format(t = datetime.datetime.now(), v = v)
        with open(self.log_file(), "a") as f:
            f.write(msg)

class GitHubRequest:
    @classmethod
    def request(cls, relative_url: str, apikey: str) -> Dict[Any, Any]:
        url = "/".join(["https://api.github.com", relative_url])
        response = requests.get(url, headers = {"Authorization": "token " + apikey})
        return response.json()

class UserInfo:
    def __init__(self, name: str, api_token: str, local_repos_folder: str):
        self.name: str = name
        self.api_token: str = api_token
        self.local_repos_folder: str = local_repos_folder

    def print(self, level: int):
        print(CMD.build_command(level, self.name))
        repos: List[Any] = list(self.request_repos())
        print(CMD.build_command(level+1, "Repositories (cloned)"))
        for repo in filter(lambda x: x.exists_locally(), repos):
            repo.print(level+1)
        print(CMD.hbar(level+1))
        print(CMD.build_command(level+1, "Repositories (remote only)"))
        for repo in filter(lambda x: not x.exists_locally(), repos):
            repo.print(level+1)

    def request_repos(self) -> Iterator[Any]:
        response: Dict[Any, Any] = GitHubRequest.request("/".join(["users", self.name, "repos"]), self.api_token)
        for repo in response:
            yield Repository(self, repo)

class Repository:
    def __init__(self, owner: UserInfo, repo_json: Dict[str, str]):
        self.owner = owner
        self.name: str = repo_json["name"]
        self.full_name: str = repo_json["full_name"]
        self.html_url: str = repo_json["html_url"]
        self.ssh_url: str = repo_json["ssh_url"]
        self.branches_url: str = repo_json["branches_url"]

    def print(self, level: int):
        repo = self.local_repo()
        color = "red"
        if repo != None:
            color = "yellow" if repo.is_dirty() else "green"
        caption = self.name
        if repo != None:
            caption += " [" + repo.active_branch.name + "]"
            caption += " (dirty)" if repo.is_dirty() else ""
        print(CMD.build_command(level, caption, color=color))
        print(CMD.build_command(level + 1, "Open"))
        print(CMD.build_command(level + 1, "Open (web)", command = "sh", command_param="open " + self.html_url))
        if repo != None:
            print(CMD.build_command(level + 1, "Open (local, folder)", command = "sh", command_param="open " + self.local_path()))
            print(CMD.build_command(level + 1, "Open (local, terminal)", command = "sh", command_param="open -a terminal " + self.local_path()))
        print(CMD.hbar(level + 1))
        print(CMD.build_command(level + 1, "Git"))
        if repo == None:
            print(CMD.build_command(level + 1, "Clone", command = "sh", command_param=Wrap.git("clone") + " " + self.ssh_url + " " + self.local_path(), refresh=True))
        else:
            print(CMD.build_command(level + 1, "Fetch", command = "sh", command_param="cd " + self.local_path() + " && " + Wrap.git("fetch")))
            print(CMD.build_command(level + 1, "Pull", command = "sh", command_param="cd " + self.local_path() + " && " + Wrap.git("pull")))
            print(CMD.build_command(level + 1, "Push", command = "sh", command_param="cd " + self.local_path() + " && " + Wrap.git("push")))
            print(CMD.build_command(level + 1, "Show log", command = "sh", command_param="cd " + self.local_path() + " && " + Wrap.git("log"), terminal=True))
            print(CMD.build_command(level + 1, "Stage"))
            print(CMD.build_command(level + 2, "All", command = "sh", command_param="cd " + self.local_path() + " && " + Wrap.git("add .")))
            print(CMD.build_command(level + 1, "Commit"))
            print(CMD.build_command(level + 2, "Staged", command = "sh", command_param="cd " + self.local_path() + " && " + Wrap.git("commit"), terminal=True))
            print(CMD.build_command(level + 2, "All", command = "sh", command_param="cd " + self.local_path() + " && " + Wrap.git("add .") + " && " + Wrap.git("commit"), terminal=True))
            print(CMD.build_command(level + 1, "Diff"))
            print(CMD.build_command(level + 2, "Changed", command = "sh", command_param="cd " + self.local_path() + " && " + Wrap.git("diff"), terminal=True))
            print(CMD.build_command(level + 2, "Staged", command = "sh", command_param="cd " + self.local_path() + " && " + Wrap.git("diff --cached"), terminal=True))
                print(CMD.build_command(level + 1, "Branches"))
                print(CMD.build_command(level + 2, "On: " + repo.active_branch.path + " ~ " + str(repo.active_branch.commit)[:7]))
                print(CMD.hbar(level+2))
                for b in repo.branches:
                    print(CMD.build_command(level + 2, b.path + " ~ " + str(b.commit)[:7]))
                    print(CMD.build_command(level + 3, "Checkout", command = "sh", command_param="cd " + self.local_path() + " && " + Wrap.git("checkout " + b.path)))
            print(CMD.hbar(level + 1))
            print(CMD.build_command(level + 1, "Utils"))
            print(CMD.build_command(level + 1, "Open in VSCode", command = "sh", command_param=Wrap.vscode(self.local_path()), terminal=False))
            print(CMD.hbar(level + 1))
            print(CMD.build_command(level + 1, "Danger zone (destructive)"))
            if repo.is_dirty():
                print(CMD.build_command(level + 1, "Git reset"))
                print(CMD.build_command(level + 2, "Soft", command = "sh", command_param="cd " + self.local_path() + " && " + Wrap.git("reset head --soft")))
                print(CMD.build_command(level + 2, "Hard", command = "sh", command_param="cd " + self.local_path() + " && " + Wrap.git("reset head --hard")))
                print(CMD.build_command(level + 1, "Delete local folder (is dirty)"))
            else:
                print(CMD.build_command(level + 1, "Git reset (not dirty)"))
                print(CMD.build_command(level + 1, "Delete local folder", command = "sh", command_param="rm -rf " + self.local_path(), refresh=True))

    def local_repo(self) -> git.Repo:
        return git.Repo(self.local_path()) if self.exists_locally() else None

    def local_path(self) -> str:
        return self.owner.local_repos_folder + "/" + self.name

    def exists_locally(self) -> bool:
        return os.path.exists(self.local_path())

def run():
    work_dir = WorkingDir(os.path.dirname(__file__) + "/.gitastic")
    work_dir.ensure()
    work_dir.log("=== ===")
    work_dir.log(datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%S"))
    work_dir.log("")
    work_dir.log(sys.argv)

    def get_user(u: List[str]) -> UserInfo:
        return UserInfo(u[0], u[1], u[2])

    def get_users() -> Iterator[UserInfo]:
        for user in USER_DATA:
            yield get_user(user)

    if len(sys.argv) == 1:
        print(CMD.build_command(0, "Gitastic"))
        print(CMD.hbar(0))
        print(CMD.build_command(0, "Users"))
        for user in get_users():
            user.print(0)
        print(CMD.hbar(0))
        print(CMD.build_command(0, "Utils"))
        print(CMD.build_command(0, "Refresh...", refresh=True))
    else:
        command: str = sys.argv[1]
        if command == "sh":
            assert(3 == len(sys.argv))
            cmd: str = base64.b64decode(sys.argv[2]).decode("UTF-8")
            work_dir.log("execute \"sh\" with \"" + cmd + "\"")
            os.system(cmd)
    work_dir.log("=== ===")

if __name__ == "__main__":
    run()
