import pathlib
import os
import json
import git
import pprint

class GitInfo():

    def __init__(self, run_config, commit_id=""):

        root_path = run_config["environment"]["version_control_root"]
        self.repo = git.Repo(root_path)

        if commit_id:
            self.commit_id = commit_id
            self.short_commit_id = commit_id[:7]
        else:
            self.commit_id = self._get_commit_id(short=False)
            self.short_commit_id = self._get_commit_id(short=True)

    def get_commit_id(self, short=False):

        commitID = self._get_commit_id(short)

        return commitID

    def _get_commit_id(self, short=False):

        sha = self.repo.head.object.hexsha

        if short:
            commit_id = self.repo.git.rev_parse(sha, short=7)
        else:
            commit_id = self.repo.git.rev_parse(sha)

        return commit_id

    def get_info_from_commit(self):
        changed_files = []

        commit = self.repo.commit(self.commit_id)
        for e in commit.tree:
            if type(e) == git.objects.blob.Blob:
                changed_files.append(e.path)
            elif type(e) == git.objects.tree.Tree:
                for t in e.blobs:
                    changed_files.append(t.path)

        info = {
            "commit_id": self.commit_id,
            "message": str(commit.message),
            "author": str(commit.author),
            "date": str(commit.committed_datetime),
            "changes": changed_files
        }

        return info

def get_commit_id(repo, short=False):

    sha = repo.head.object.hexsha
    if short:
        commit_id = repo.git.rev_parse(sha, short=7)
    else:
        commit_id = repo.git.rev_parse(sha)

    return commit_id


def get_info_from_commit(commit):

    info = {
        "commit_id": commit,
        "message": str(commit.message),
        "author": str(commit.head.object.author),
        "date": str(commit.head.object.committed_datetime),
        "updates": "files"
    }

    return info


def get_file_history(repo, path):
    commits_touching_path = list(repo.iter_commits(paths=path))

    for each in commits_touching_path:
        print(each)


def list_modified_files(run_config):
    """
    List modified files in the project and marks them with
    A: Add
    D: Delete
    M: Modified
    """

    root_path = run_config["environment"]["version_control_root"]
    repo = git.Repo(root_path)

    modified_files = {}
    for each_diff_object in repo.index.diff(None):
        # print(each_diff_object.change_type)
        modified_files[each_diff_object.a_path] = {"change_type": each_diff_object.change_type}

    return modified_files


def list_submodules(run_config):
    """List the submodules in the project
    TODO: Make sure that we handle recursive submodules
    """
    root_path = run_config["environment"]["version_control_root"]
    repo = git.Repo(root_path)

    submodule_report = {}

    for each_submodule in repo.submodules:
        sub_repo = each_submodule.module()
        submodule_report[each_submodule.name] = {"submodules": sub_repo.submodules}
        print(each_submodule.name)
        # pprint.pprint(dir(sub_repo))
        # each_submodule.update(init=True)
        # pprint.pprint(dir(each_submodule.repo))
        # a = each_submodule.repo.git.execute("git status")
        # pprint.pprint(dir(each_submodule))
        # each_submodule.update()

    return submodule_report


def update_sentinel_config(run_config):
    """Adds version control information from the current commit to the config file"""

    config_folder_abs_path = run_config["environment"]["sentinel_config_root_path"]
    project_root_path = run_config["environment"]["version_control_root"]
    path = pathlib.Path(config_folder_abs_path)

    version_control_root_path = path.joinpath("gen_version_control")

    if not version_control_root_path.exists():
        os.makedirs(version_control_root_path)

    repo = git.Repo(project_root_path)
    commit_id = get_commit_id(repo)

    for each_file in repo.head.object.stats.files:
        get_file_history(repo, each_file)

    simple_info = {
        "commit_id": commit_id,
        "message": str(repo.head.object.message),
        "author": str(repo.head.object.author),
        "date": str(repo.head.object.committed_datetime),
        "updates": "files"
    }

    pprint.pprint(simple_info)

    version_control_file = version_control_root_path.joinpath("gen_vcs_info.json")

    f = open(version_control_file, "w")
    f.write(json.dumps(simple_info, indent=4))
    f.close()


def write_history_file(environment_config, commit_id):
    """
    Writes an info file about the commit
    """

    walker = GitRepoWalker(environment_config)

    path = pathlib.Path(environment_config["environment"]["sentinel_artifacts_path"]).joinpath("vcs_info.json")
    entry = walker.get_entry_from_commit_id(commit_id)

    f = open(path, "w")
    f.write(json.dumps(entry, indent=4))
    f.close()


class GitRepoWalker:

    def __init__(self, environment_config):
        project_root_path = environment_config["environment"]["version_control_root"]

        self.repo = git.Repo(project_root_path)
        self.commits = []
        self.commit_ids = []
        self.history = self._construct_git_history()
        self.current_commit = ""

    def _clean_repo(self):
        self.repo.git.reset("--hard")
        self.repo.git.clean("-dfx")

    def clean_checkout_commit(self, commit_id):
        self._clean_repo()
        self.repo.git.checkout(commit_id)

        self.current_commit = commit_id

    @staticmethod
    def _create_json_entry_for_commit(commit):

        entry = {"commit_time": str(commit.committed_datetime),
                 "commit_sha": str(commit.hexsha),
                 "comitter": str(commit.committer),
                 "message": commit.message,
                 "changes": commit.stats.files}

        return entry

    def get_entry_from_commit_id(self, commit_id):

        entry = ""
        for commit in self.repo.iter_commits():
            if str(commit.hexsha).startswith(commit_id):
                entry = self._create_json_entry_for_commit(commit)
                break

        if not entry:
            print("Error: %s not found in history", commit_id)

        return entry

    def _construct_git_history(self):

        root = {}
        for commit in self.repo.iter_commits():
            root[commit.hexsha] = self._create_json_entry_for_commit(commit)

            # Todo refactor whatever uses the commits to user the json file
            self.commits.append(commit)
            self.commit_ids.append(commit.hexsha)

        return root
