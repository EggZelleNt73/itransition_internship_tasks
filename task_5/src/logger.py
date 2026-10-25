import logging 
import inspect
from src.configs import LOGGER_CONFIG


logging.basicConfig(
    level=LOGGER_CONFIG["level"],
    format=LOGGER_CONFIG["format"],
    datefmt=LOGGER_CONFIG["date_format"]
)


class DynamicLogger:
    @property
    def _get_logger(self) -> logging.Logger:
        current_frame = inspect.currentframe()
        if not current_frame:
            return logging.getLogger("__main__")
            
        caller_frame = current_frame.f_back
        while caller_frame:
            caller_path = caller_frame.f_code.co_filename
            module_name = inspect.getmodulename(caller_path)
            if module_name and module_name != "logger":
                break   
            caller_frame = caller_frame.f_back
        else:
            module_name = "__main__"

        return logging.getLogger(module_name)


    def info(self, msg, *args, **kwargs):
        kwargs.setdefault('stacklevel', 2)
        self._get_logger.info(msg, *args, **kwargs)


    def warning(self, msg, *args, **kwargs):
        kwargs.setdefault('stacklevel', 2)
        self._get_logger.warning(msg, *args, **kwargs)


    def error(self, msg, *args, **kwargs):
        kwargs.setdefault('stacklevel', 2)
        self._get_logger.error(msg, *args, **kwargs)


logger = DynamicLogger()
