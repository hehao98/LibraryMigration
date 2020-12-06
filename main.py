import sys
import logging

if __name__ == "__main__":
    logging.basicConfig(
        format="%(asctime)s (Process %(process)d) [%(levelname)s] %(filename)s:%(lineno)d %(message)s",
        level=logging.INFO)

    logging.info("Start!")
    __import__(sys.argv[1]).run()
    logging.info("Finish!")
