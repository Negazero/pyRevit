import sys
import clr

from pyrevit import HOME_DIR, EXEC_PARAMS
from pyrevit.coreutils import Timer, find_loaded_asm
from pyrevit.coreutils.logger import get_logger, stdout_hndlr
from pyrevit.repo import PYREVIT_VERSION
from pyrevit.userconfig import user_config

from pyrevit.extensions.extmanager import get_installed_ui_extensions

from pyrevit.loader.interfacetypes import LOADER_BASE_NAMESPACE, BASE_CLASSES_ASM_NAME
from pyrevit.loader.asmmaker import create_assembly
from pyrevit.loader.uimaker import update_pyrevit_ui, cleanup_pyrevit_ui

# noinspection PyUnresolvedReferences
from System.Diagnostics import Process


logger = get_logger(__name__)


def _setup_output_window():
    # import module with ScriptOutput and ScriptOutputStream types (base classes module)
    base_asm = find_loaded_asm(LOADER_BASE_NAMESPACE, by_partial_name=True)
    clr.AddReference(base_asm)
    base_module = __import__(LOADER_BASE_NAMESPACE)

    # create output window and assign handle
    out_window = base_module.ScriptOutput()
    EXEC_PARAMS.window_handle = out_window.Handle

    # create output stream and set stdout to it
    outstr = base_module.ScriptOutputStream(out_window)
    sys.stdout = outstr
    sys.stderr = outstr
    stdout_hndlr.stream = outstr


def _perform_onsessionload_operations():
    pass


def _perform_onstartup_operations():
    pass


def _report_env():
    # log python version, home directory, config file, ...
    pyrvt_ver = PYREVIT_VERSION.get_formatted()
    logger.info('pyRevit version: {} - :coded: with :small-black-heart: in Portland, OR'.format(pyrvt_ver))
    logger.info('Running on: {}'.format(sys.version))
    logger.info('Home Directory is: {}'.format(HOME_DIR))
    logger.info('Base assembly is: {}'.format(BASE_CLASSES_ASM_NAME))
    logger.info('Config file is: {}'.format(user_config.config_file))



def _new_session():
    # for every extension of installed extensions, create an assembly, and create a ui
    # get a list of all directories that could include extensions
    pkg_search_dirs = user_config.get_ext_root_dirs()
    logger.debug('Extension Directories: {}'.format(pkg_search_dirs))

    # collect all library extensions. Their dir paths need to be added to sys.path for all commands
    for root_dir in pkg_search_dirs:
        # Get a list of all installed extensions in this directory
        # _parser.get_installed_extension_data() returns a list of extensions in given directory
        # then iterater through extensions and load one by one
        for ui_ext in get_installed_ui_extensions(root_dir):
            # create a dll assembly and get assembly info
            ext_asm_info = create_assembly(ui_ext)
            if not ext_asm_info:
                logger.critical('Failed to create assembly for: {}'.format(ui_ext))
                continue

            logger.info('Extension assembly created: {}'.format(ui_ext.name))

            # update/create ui (needs the assembly to link button actions to commands saved in the dll)
            update_pyrevit_ui(ui_ext, ext_asm_info)
            logger.info('UI created for extension: {}'.format(ui_ext.name))

    cleanup_pyrevit_ui()


def load_session():
    """Handles loading/reloading of the pyRevit addin and extensions.
    To create a proper ui, pyRevit extensions needs to be properly parsed and a dll assembly needs to be created.
    This function handles both tasks through interactions with .extensions and .coreutils

    Usage Example:
        from pyrevit.loader import load_session
        load_session()
    """

    # initialize timer
    timer = Timer()

    if EXEC_PARAMS.window_handle is None:
        _setup_output_window()

    # report environment conditions
    _report_env()

    _new_session()

    _perform_onsessionload_operations()
    _perform_onstartup_operations()

    # log load time
    endtime = timer.get_time()
    logger.info('Load time: {} seconds {}'.format(endtime, ':ok_hand_sign:' if endtime < 3.00 else ':thumbs_up:'))
