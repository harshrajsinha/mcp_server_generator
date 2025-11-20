import logging.config
import time
import os
import colorama
from pythonjsonlogger.jsonlogger import JsonFormatter
# Initialize colorama for cross-platform color support
colorama.init()


class ColoredJsonFormatter(JsonFormatter):
    """Custom JSON formatter with color support for console output"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.COLORS = {
            'ERROR': colorama.Fore.RED,
            'WARNING': colorama.Fore.YELLOW,
            'INFO': colorama.Fore.GREEN,
            'DEBUG': colorama.Fore.BLUE,
            'CRITICAL': colorama.Fore.RED + colorama.Style.BRIGHT
        }

    def format(self, record):
        json_str = super().format(record)
        if record.levelname in self.COLORS and LOG_CONSOLE in (1, '1', True, 'True'):
            color = self.COLORS[record.levelname]
            return f"{color}{json_str}{colorama.Style.RESET_ALL}"
        return json_str


# Rest of your existing configuration...
BASE_DIR_MAIN = os.environ.get("BASE_DIR_MAIN", 'log')
if not os.path.exists(BASE_DIR_MAIN):
    os.makedirs(BASE_DIR_MAIN, exist_ok=True)

LOG_FILE = os.environ.get("LOG_FILE", False)
LOG_CONSOLE = os.environ.get("LOG_CONSOLE", False)
LOG_STASH = os.environ.get("LOG_STASH", False)
LOGSTASH_PORT = os.environ.get("LOGSTASH_PORT", 5959)
LOGSTASH_IP = os.environ.get("LOGSTASH_IP", 'localhost')

if LOG_STASH in (1, '1', True, 'True'):
    from logstash_formatter import LogstashFormatterV1

ALLOWED_LOG_LEVEL = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
LOG_LEVEL = os.environ.get("LOG_LEVEL", 'INFO')
LOG_LEVEL = "INFO" if LOG_LEVEL.strip().upper() not in ALLOWED_LOG_LEVEL else LOG_LEVEL.strip().upper()

LOG_TAG = os.environ.get("LOG_TAG", 'Scikiq Utils')


def getLogger(
        rootPath,
        changeLocation=False,
        logFile=LOG_FILE,
        logConsole=LOG_CONSOLE,
        logStash=LOG_STASH,
        logStashIP=LOGSTASH_IP,
        logStashPort=LOGSTASH_PORT,
        level=LOG_LEVEL,
        tags=LOG_TAG,
        tags_audit='Scikiq Audit'
):
    logging_config = {
        'version': 1,
        'disable_existing_loggers': True,
        'formatters': {
            'verbose': {
                'format': '%(levelname)s %(asctime)s %(module)s %(process)d %(thread)d %(message)s'
            },
            'simple': {
                'format': '%(levelname)s %(message)s'
            },
            'json': {
                '()': ColoredJsonFormatter,
                'format': '%(asctime)s %(levelname)s %(message)s'
            }
        },
        'handlers': {},
        'loggers': {}
    }

    handlers = []
    audit_handlers = []

    if logConsole in (1, '1', True, 'True'):
        handlers.append("console")
        audit_handlers.append("console")
        logging_config['handlers']['console'] = {
            'level': level,
            'class': 'logging.StreamHandler',
            'formatter': 'json'
        }

    if logStash in (1, '1', True, 'True'):
        handlers.append("logstash")
        logging_config['handlers']['logstash'] = {
            'level': level,
            'class': 'logstash.TCPLogstashHandler',
            'host': logStashIP,
            'port': logStashPort,
            'version': 1,
            'message_type': 'django',
            'fqdn': False,
            'tags': [tags],
        }

        audit_handlers.append("logstash_audit")
        logging_config['handlers']['logstash_audit'] = {
            'level': level,
            'class': 'logstash.TCPLogstashHandler',
            'host': logStashIP,
            'port': logStashPort,
            'version': 1,
            'message_type': 'django',
            'fqdn': False,
            'tags': [tags_audit],
        }

    if logFile in (1, '1', True, 'True'):
        handlers.append("file")
        create_file_name = "log/scikiq-" + time.strftime("%Y-%m-%d") + ".txt"

        if changeLocation:
            log_dir = os.path.join(rootPath, 'log')
            if not os.path.isdir(log_dir):
                os.makedirs(log_dir)
            create_file_name = os.path.join(rootPath, "log/scikiq-" + time.strftime("%Y-%m-%d") + ".txt")

        logging_config['handlers']['file'] = {
            'level': level,
            'class': 'logging.FileHandler',
            'filename': create_file_name,
            'mode': 'a',
            'formatter': 'json',
        }

    logging_config['loggers'] = {
        'application': {
            'handlers': handlers,
            'propagate': True,
            'level': level,
        },
        'audit': {
            'handlers': audit_handlers,
            'propagate': True,
            'level': "INFO",
        },
    }

    logging.config.dictConfig(logging_config)
    logger = logging.getLogger('application')

    handler = logging.StreamHandler()
    if LOG_STASH in (1, '1', True, 'True'):
        formatter = LogstashFormatterV1()
        handler.setFormatter(formatter)
        logger.addHandler(handler)

    return logger, logging.getLogger('audit')




skq_logger, audit_log = getLogger(BASE_DIR_MAIN)
skq_logger.info("SCIKIQ_DBUTILS LOGS INFO STARTED")
