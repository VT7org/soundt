
# All rights reserved.
#


class AssistantErr(Exception):
    def __init__(self, errr: str):
        super().__init__(errr)


class UnableToFetchCarbon(Exception):
    pass

def is_ignored_error(err: Union[Exception, BaseException]) -> bool:
    """
    Determine if the error should be skipped from full logging.
    Matches:
    - Exception type (if enabled)
    - Known substrings in error message
    """
    if isinstance(err, IGNORED_EXCEPTION_CLASSES):
        return True

    err_str = str(err).lower()
    return any(keyword.lower() in err_str for keyword in IGNORED_ERROR_KEYWORDS)
