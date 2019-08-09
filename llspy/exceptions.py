class LLSpyError(Exception):
    """
    Generic exception indicating anything relating to the execution
    of LLSpy. A string containing an error message should be supplied
    when raising this exception.
    """

    pass


class ParametersError(LLSpyError):
    """
    Exception indicating something is wrong with the parameters for preview
    or processing. A string containing an error message should be supplied
    when raising this exception.
    """

    pass


class CompressionError(LLSpyError):
    """
    Exception indicating something went wrong with compression or decompression
    of an LLSdir.
    """

    pass


class CUDAbinException(LLSpyError):
    """
    Generic exception indicating anything relating to the execution
    of cudaDeconDeskew. A string containing an error message should be supplied
    when raising this exception.
    """

    pass


class CUDAProcessError(CUDAbinException):
    """
    Exception to describe an cudaDeconv execution error.
    """

    def __init__(self, cmd, rtnCode, output):
        """
        cmd -- The string or byte array of the cudaDeconv command ran
        rtnCode -- The process return code
        output -- Any output from the failed process
        """
        self.cmd = cmd
        self.rtnCode = rtnCode
        self.output = output
        self.message = "cudaDeconv returned a non-zero exit code"


class LibCUDAException(LLSpyError):
    """
    Error indicating something wrong with libcudaDeconv.
    """

    pass


class SettingsError(LLSpyError):
    pass


class OTFError(LLSpyError):
    pass
