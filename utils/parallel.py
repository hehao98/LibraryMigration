# Run func(arg) concurrently (return pd.DataFrame or None)
# hehao98 <heh@pku.edu.cn> - Unknown

from pathos.pools import ProcessPool
from tqdm import tqdm
import time
import pandas as pd
import numpy as np
import os

# 并行框架
def parallel(func, core_num, *args, progress_bar=tqdm, return_df=True):
    pool = ProcessPool(core_num)
    try:
        start = time.time()
        # imap方法
        with progress_bar(total=len(args[0]), desc="计算进度") as t:  # 进度条设置
            if return_df:  # return dataframe
                r = pd.DataFrame()
                for i in pool.imap(func, *args):
                    r = r.append(i, ignore_index=True)
                    t.set_postfix({'并行函数': func.__name__, "计算花销": "%ds" % (time.time() - start)})
                    t.update()
                return r
            else:  # return nothing
                for i in pool.imap(func, *args):
                    t.set_postfix({'并行函数': func.__name__, "计算花销": "%ds" % (time.time() - start)})
                    t.update()
    except Exception as e:
        print(e)
    finally:
        # 关闭池
        pool.close()  # close the pool to any new jobs
        pool.join()  # cleanup the closed worker processes
        pool.clear()  # Remove server with matching state


def process_worker(func, args_list, progress_bar=tqdm, return_df=True):
    r = pd.DataFrame()
    pid = os.getpid()
    start = time.time()
    with progress_bar(total=len(df), desc="计算进度") as t:  # 进度条设置
        for arg in args_list:
            if return_df:
                r = r.append(func(arg), ignore_index=True)
            else:
                func(arg)
            t.set_postfix({"pid": pid, "time": "%ds" % (time.time() - start)})
            

