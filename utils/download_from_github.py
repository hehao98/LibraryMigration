# Clone a repo from Github
# 12f23eddde <rzhe@pku.edu.cn> - Apr 12 2021
import git
import os
import pandas as pd
import numpy as np
import requests


def clone_project_from_github(owner: str, repo: str, branch='master',REPOS_DIR='repos/', proxy=None):
    path = os.path.abspath(f'{REPOS_DIR}/{owner}/{repo}/{branch}')

    if not os.path.exists(path):
        os.makedirs(path)

    git_config=f"http.proxy={proxy}" if proxy else None
    git.Repo.clone_from(f'http://github.com/{owner}/{repo}.git', to_path=path, branch=branch, 
        config=git_config)
    
    
def download_file_from_github(owner:str, repo: str, branch='master', file='requirements.txt', overwrite=True, proxy=None, REPOS_DIR='repos/') -> bool:
    requests_proxies = {
        "http": f"{proxy}",
        'https': f"{proxy}"
    } if proxy else None
    
    url = f"https://raw.githubusercontent.com/{owner}/{repo}/{branch}/{file}"
    
    try:
        r = requests.get(url=url, proxies=requests_proxies)
    except FileNotFoundError:
        return False
    
    # create folder, place file owner/repo/branch/file
    if not os.path.exists(f"{REPOS_DIR}/{owner}/{repo}/{branch}"):
        os.makedirs(f"{REPOS_DIR}/{owner}/{repo}/{branch}")
        
    # do not overwrite if file exists
    if not overwrite and os.path.exists(f"{REPOS_DIR}/{owner}/{repo}/{branch}/{file}"):
        return False
    
    if r.status_code != 200:
        return False
    
    save_path = '/'.join(f"{REPOS_DIR}/{owner}/{repo}/{branch}/{file}".split('/')[:-1])
    
    if not os.path.exists(save_path):
        os.makedirs(save_path)
    
    with open(f"{REPOS_DIR}/{owner}/{repo}/{branch}/{file}", 'w+') as f:
        f.write(r.text)
        
    return True
    
    
if __name__ == '__main__':
    clone_project_from_github('requests', 'requests-oauthlib', REPOS_DIR='./tests/', proxy='socks5://10.128.188.189:1081')
    download_file_from_github('requests', 'requests-oauthlib', REPOS_DIR='./tests/', proxy='socks5://10.128.188.189:1081')