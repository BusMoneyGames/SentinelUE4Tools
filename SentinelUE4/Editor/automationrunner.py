import subprocess
import Editor.editorutilities as editorutilities

def run_automation_test(run_config):

    util = editorutilities.UE4EditorUtilities(run_config)
    
    automation_tool_path = util.get_unreal_automation_tool_path()
    cmd = automation_tool_path.as_posix() + " -list"
    print(cmd)

    subprocess.call(cmd)

def run_tests(run_config):

    util = editorutilities.UE4EditorUtilities(run_config)

    editor_exe = util.get_editor_executable_path()

    project_path = util.get_project_file_path()

    cmd = editor_exe.as_posix() + " " + project_path.as_posix() + " -ExecCmds=Automation RunTests SourceTests -unattend -game"
    subprocess.call(cmd)

    """
    UE4Editor.exe path/to/project/TestProject.uproject
              -ExecCmds="Automation RunTests SourceTests"
              -unattended
              -nopause
              -testexit="Automation Test Queue Empty"
              -log=output.txt
              -game
    """
