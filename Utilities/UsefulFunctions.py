
def is_interactive():
    '''Check if the script is running in a notebook'''
    try:
        # Script is running in a notebook
        get_ipython()
        return True
    except NameError:
        # Not running in a notebook
        return False