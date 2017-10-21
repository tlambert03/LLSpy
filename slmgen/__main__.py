try:
    from .slmwindow import main
except ImportError:
    import os
    import sys
    thisDirectory = os.path.dirname(os.path.abspath(__file__))
    sys.path.append(os.path.join(thisDirectory, os.pardir))
    from slmgen.slmwindow import main

if __name__ == '__main__':

    import logging
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.DEBUG)

    main()
