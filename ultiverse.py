"""
chain: opBNB
chainID: 204
RPC: https://opbnb-mainnet-rpc.bnbchain.org
"""
import json
from datetime import datetime

from curl_cffi.requests import AsyncSession

from web3 import AsyncWeb3
from eth_account.messages import encode_defunct

import fake_useragent
from diskcache import Cache
from datetime import datetime, timedelta
import traceback

import re
import random
from loguru import logger
import asyncio

op_chain_id = 204
op_rpc = "https://opbnb-mainnet-rpc.bnbchain.org"
cache = Cache('./pilot')

timeout = 5
try_times = 5
'''
1、获取登录签名信息
2、登录 附带邀请码
3、获取mint签名
4、mint
5、提交mint

1、获取登录签名信息
2、登录 附带邀请码
3、发送签到交易
4、提交签到
'''
# 代理放在这个列表
proxies_list = [
]

def get_today_expired():
    # 获取当前时间
    now = datetime.now()

    # 构造明天0点的时间
    midnight = datetime(now.year, now.month, now.day) + timedelta(days=1)

    # 计算差值的秒数
    seconds_to_midnight = (midnight - now).total_seconds()

    return int(seconds_to_midnight)

def get_proxy():
    proxy = random.choice(proxies_list)
    proxies = {
        'http': proxy,
        'https': proxy
    }
    return proxies

class Pilot:
    def __init__(self, private, addr, ua, proxies = None):
        self.http = AsyncSession(timeout=60)
        self.private = private
        
        self.ua = ua
        self.proxies = proxies

        # 初始化钱包
        self.web3 = AsyncWeb3(AsyncWeb3.AsyncHTTPProvider(op_rpc))
        self.account = self.web3.eth.account.from_key(private)
        self.addr = self.web3.to_checksum_address(self.account.address)

        # 初始化合约
        self.set_mint_contract()
        self.set_explore_contract()

    # 设置mint合约
    def set_mint_contract(self):
        abi = [
            {
                "inputs": [
                    {"internalType": "uint256", "name": "deadline", "type": "uint256"},
                    {"internalType": "bytes32", "name": "attributeHash", "type": "bytes32"},
                    {"internalType": "bytes", "name": "signature", "type": "bytes"}
                ],
                "name": "mintSBT",
                "outputs": [],
                "stateMutability": "nonpayable",
                "type": "function"
            }
        ]
        address = self.web3.to_checksum_address("0x06f9914838903162515afa67d5b99ada0f9791cc")
        self.mint_contract = self.web3.eth.contract(address=address, abi=abi)

    # 设置探索合约
    def set_explore_contract(self):
        abi = [
            {
                "inputs": [
                    {
                        "internalType": "uint256",
                        "name": "deadline",
                        "type": "uint256"
                    },
                    {
                        "internalType": "uint256",
                        "name": "voyageId",
                        "type": "uint256"
                    },
                    {
                        "internalType": "uint16[]",
                        "name": "destinations",
                        "type": "uint16[]"
                    },
                    {
                        "internalType": "bytes32",
                        "name": "data",
                        "type": "bytes32"
                    },
                    {
                        "internalType": "bytes",
                        "name": "signature",
                        "type": "bytes"
                    }
                ],
                "name": "explore",
                "outputs": [],
                "stateMutability": "nonpayable",
                "type": "function"
            }
        ]
        address = self.web3.to_checksum_address("0x16d4c4b440cb779a39b0d8b89b1590a4faa0215d")
        self.expore_contract = self.web3.eth.contract(address=address, abi=abi)

    def get_sec_headers(self, user_agent):
        # 尝试从 User Agent 中提取浏览器名称和版本信息
        browser_info_match = re.search(r'(.+?)/(\d+\.\d+)', user_agent)
        browser_info = browser_info_match.group(1) if browser_info_match else None
        version_info = browser_info_match.group(2) if browser_info_match else None

        # 尝试从 User Agent 中提取平台信息
        platform_info_match = re.search(r'\((.+?)\)', user_agent)
        platform_info = platform_info_match.group(1) if platform_info_match else None

        # 如果提取不到，随机生成
        if not browser_info:
            browser_info = random.choice(['Chromium', 'Google Chrome'])

        if not version_info:
            version_info = f'{random.randint(70, 90)}.0'  # 随机生成版本号，范围可以根据实际情况调整

        if not platform_info:
            platform_info = random.choice(['Windows NT 10.0', 'Macintosh; Intel Mac OS X 10_15_7'])

        # 构造 Sec-CH-UA 头部的内容
        sec_ch_ua = f'{browser_info};v={version_info}'

        # 构造 sec-ch-ua-platform 头部的内容
        sec_ch_ua_platform = f'{platform_info}'

        return sec_ch_ua, sec_ch_ua_platform

    def get_header(self, token = None):
        sec_ua, platform = self.get_sec_headers(self.ua)
        headers = {
            "authority": "toolkit.ultiverse.io",
            "accept": "application/json, text/plain, */*",
            "accept-language": "ja",
            "cache-control": "no-cache",
            "content-type": "application/json",
            "cookie": "_ga=GA1.1.1908045894.1709548703; _ga_2XR1HXN03L=GS1.1.1709548702.1.1.1709548732.0.0.0",
            "origin": "https://pilot.ultiverse.io",
            "pragma": "no-cache",
            "referer": "https://pilot.ultiverse.io/",
            'sec-ch-ua': sec_ua,
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": f'"{platform}"',
            "sec-fetch-dest": "empty",
            "sec-fetch-mode": "cors",
            "sec-fetch-site": "same-site",
            "ul-auth-api-key": "YWktYWdlbnRAZFd4MGFYWmxjbk5s",
            'user-agent': self.ua,
        }
        if token is not None:
            headers['ul-auth-address'] = self.addr
            headers['ul-auth-token'] = token
        return headers
        
    # 获取登录签名
    async def wallet_sign(self):
        # 请求签名文本
        url = f"https://account-api.ultiverse.io/api/user/signature"
        headers = self.get_header()

        data = {"address":self.addr,"feature":"assets-wallet-login","chainId":op_chain_id}

        resp = None
        for i in range(5):
            try:
                resp = await self.http.post(url, headers=headers, json=data, proxies=self.proxies, impersonate="chrome")
                break
            except Exception as e:
                await self.switch_proxy()
                logger.error(f"{self.addr} : 获取签名异常:{e}")
                continue

        if resp is None:
            logger.error(f"{self.addr} : 获取签名完全失败")
            return False
        
        if resp.status_code != 201:
            logger.error(f"{self.addr} : 获取签名文本失败:{resp.text}")
            return False
        
        resp_json = json.loads(resp.text)
        if not resp_json['success']:
            logger.error(f"{self.addr} : 获取签名文本失败:{resp.text}")
            return False

        # 进行签名数据
        signature = self.account.sign_message(encode_defunct(text=resp_json['data']['message']))
        sign = signature.signature.hex()
        return sign

    # 登录
    async def login(self):
        # 检查缓存中的数据
        cache_key = f"login_{self.addr}"
        token = cache.get(cache_key)
        if token is not None:
            return token
        
        sign = await self.wallet_sign()
        if not sign:
            return False
        
        url = 'https://account-api.ultiverse.io/api/wallets/signin'
        headers = self.get_header()
        data = {"address":self.addr,"signature":sign,"chainId":op_chain_id}
        resp = None
        for i in range(5):
            try:
                resp = await self.http.post(url, headers=headers, json=data, proxies=self.proxies, timeout=timeout, impersonate="chrome")
                break
            except Exception as e:
                logger.error(f"{self.addr} : 登录异常:{e}")
                await self.switch_proxy()
                continue
        if resp is None:
            logger.error(f"{self.addr} : 登录完全失败")
            return False
        
        if resp.status_code != 201:
            logger.error(f"{self.addr} : 登录失败1:{resp.text}")
            return False

        resp_json = json.loads(resp.text)

        if not resp_json['success']:
            logger.error(f"{self.addr} : 登录失败2:{resp.text}")
            return False
        
        if "data" not in resp_json:
            logger.error(f"{self.addr} : 登录失败3: {resp.text}")
            return False
        token = resp_json['data']['access_token']

        # 换成登录信息
        cache.set(cache_key, token, expire=get_today_expired())
        return token

    # 设置邀请码
    async def invite(self, token):
        # 检查缓存中的数据
        cache_key = f"login_invite_{self.addr}"
        is_succ = cache.get(cache_key)
        if is_succ is not None:
            return is_succ
        
        url = 'https://pml.ultiverse.io/api/register/sign'
        headers = self.get_header(token=token)
        invite_code="nXXey"
        data = {"address":self.addr,"referralCode":invite_code,"chainId":op_chain_id}
        resp = None
        for i in range(5):
            try:
                resp = await self.http.post(url, headers=headers, json=data, proxies=self.proxies, timeout=timeout, impersonate="chrome")
                break
            except Exception as e:
                logger.error(f"{self.addr} : 设置邀请异常:{e}")
                await self.switch_proxy()
                continue
        if resp is None:
            logger.error(f"{self.addr} : 设置邀请完全失败")
            return False
        
        if resp.status_code != 201:
            logger.error(f"{self.addr} : 设置邀请失败1:{resp.text}")
            return False

        resp_json = json.loads(resp.text)

        if not resp_json['success']:
            logger.error(f"{self.addr} : 设置邀请失败2:{resp.text}")
            return False
        
        if "data" not in resp_json:
            logger.error(f"{self.addr} : 设置邀请失败3: {resp.text}")
            return False

        # 换成登录信息
        cache.set(cache_key, 1)
        return resp_json['data']['success']

    # 设置昵称
    async def set_nick_name(self, token):
        # 检查缓存中的数据
        cache_key = f"login_set_nickname_{self.addr}"
        is_succ = cache.get(cache_key)
        if is_succ is not None:
            return is_succ
        
        url = 'https://pml.ultiverse.io/api/register/pilot'
        headers = self.get_header(token=token)

        data = {"nickname":"a" + self.addr[-8:].lower()}
        resp = None
        for i in range(5):
            try:
                resp = await self.http.post(url, headers=headers, json=data, proxies=self.proxies, timeout=timeout, impersonate="chrome")
                break
            except Exception as e:
                logger.error(f"{self.addr} : 设置昵称异常:{e}")
                await self.switch_proxy()
                continue
        if resp is None:
            logger.error(f"{self.addr} : 设置昵称完全失败")
            return False
        if resp.status_code != 201:
            logger.error(f"{self.addr} : 设置昵称失败1:{resp.text}")
            return False

        resp_json = json.loads(resp.text)

        if not resp_json['success']:
            logger.error(f"{self.addr} : 设置昵称失败2:{resp.text}")
            return False
        
        if "data" not in resp_json:
            logger.error(f"{self.addr} : 设置昵称失败3: {resp.text}")
            return False

        # 换成登录信息
        cache.set(cache_key, 1)
        return resp_json['data']['success']
    
    # mint nft
    async def mint(self, token):
        # 检查缓存中的数据
        cache_key = f"login_mint_{self.addr}"
        is_succ = cache.get(cache_key)
        if is_succ is not None:
            return is_succ
        
        url = 'https://pml.ultiverse.io/api/register/mint'
        headers = self.get_header(token=token)
        a = ['Optimistic','Introverted', 'Adventurous']
        b = ['Sensitive','Confident', 'Curious']
        c = ['Practical','Social Butterfly', 'Independent']
        d = ['Responsible','Open-minded', 'Humorous']
        e = ['Grounded','Skeptical', 'Altruistic']
        meta = [random.choice(a), random.choice(b), random.choice(c) ,random.choice(d), random.choice(e)]
        data = {"meta":meta}
        resp = None
        for i in range(5):
            try:
                resp = await self.http.post(url, headers=headers, json=data, proxies=self.proxies, timeout=timeout, impersonate="chrome")
                break
            except Exception as e:
                logger.error(f"{self.addr} : 获取mint信息异常:{e}")
                await self.switch_proxy()
                continue
        if resp is None:
            logger.error(f"{self.addr} : 获取mint信息完全失败")
            return False
        
        if resp.status_code != 201:
            logger.error(f"{self.addr} : 获取mint信息失败1:{resp.text}")
            return False

        resp_json = json.loads(resp.text)


        if not resp_json['success']:
            logger.error(f"{self.addr} : 获取mint信息失败2:{resp.text}")
            return False
        
        if "data" not in resp_json:
            logger.error(f"{self.addr} : 获取mint信息失败3: {resp.text}")
            return False

        mint_info = resp_json['data']
        # 调用合约
        gas_price = await self.web3.eth.gas_price
        mint_func = self.mint_contract.functions.mintSBT(int(mint_info['deadline']), mint_info['attributeHash'], mint_info['signature'])
        for i in range(5):
            try:
                if mint_func is None:
                    return False
                nonce = await self.web3.eth.get_transaction_count(self.account.address)
                tx = await mint_func.build_transaction({
                    'from': self.addr,
                    'chainId': op_chain_id,
                    'gas': gas_price,
                    'nonce': nonce,
                    'gas':0,
                    'maxFeePerGas': 18,
                    'maxPriorityFeePerGas': 2,
                })
                gas = int(await self.web3.eth.estimate_gas(tx))
                tx.update({'gas' : gas})

                sign = self.account.sign_transaction(tx)
                tx_id = await self.web3.eth.send_raw_transaction(sign.rawTransaction)
                receipt = await self.web3.eth.wait_for_transaction_receipt(tx_id)
                if receipt.status == 1:
                    logger.success(f"{self.addr} mint成功 {tx_id.hex()}")
                    cache.set(cache_key, 1)
                    return True
                else:
                    logger.error(f"{self.addr}  发送mint失败 {tx_id.hex()}")
            except Exception as e:
                logger.error(f"[{self.addr}] 发送mint失败{e}")
                await self.switch_proxy()
                continue
        logger.error(f"[{self.addr}] 发送mint完全失败")
        return False

    # 获取探索列表
    async def get_explore_list(self, token):
        # 检查缓存中的数据
        cache_key = f"explore_list"
        is_succ = cache.get(cache_key)
        if is_succ is not None:
            return is_succ
        
        url = 'https://pml.ultiverse.io/api/explore/list'
        headers = self.get_header(token=token)

        resp = await self.http.get(url, headers=headers, proxies=self.proxies, timeout=timeout, impersonate="chrome")

        if resp.status_code != 200:
            logger.error(f"{self.addr} : 获取探索列表失败1:{resp.text}")
            return False

        resp_json = json.loads(resp.text)

        if not resp_json['success']:
            logger.error(f"{self.addr} : 获取探索列表失败2:{resp.text}")
            return False
        
        if "data" not in resp_json:
            logger.error(f"{self.addr} : 获取探索列表失败3: {resp.text}")
            return False

        cache.set(cache_key, resp_json['data'], expire=get_today_expired())

        return resp_json['data']
    
    # 获取余额
    async def get_balance(self, token):        
        url = 'https://pml.ultiverse.io/api/profile'
        headers = self.get_header(token=token)

        resp = await self.http.get(url, headers=headers, proxies=self.proxies, timeout=timeout, impersonate="chrome")

        if resp.status_code != 200:
            logger.error(f"{self.addr} : 获取余额失败1:{resp.text}")
            return False

        resp_json = json.loads(resp.text)

        if not resp_json['success']:
            logger.error(f"{self.addr} : 获取余额失败2:{resp.text}")
            return False
        
        if "data" not in resp_json:
            logger.error(f"{self.addr} : 获取余额失败3: {resp.text}")
            return False

        return resp_json['data']
    
    # 开始探索
    async def explore(self, token, world_ids = ['Terminus']):
        cache_key = f"explore_{self.addr}"
        is_succ = cache.get(cache_key)
        if is_succ is not None:
            return is_succ
        
        url = 'https://pml.ultiverse.io/api/explore/sign'
        headers = self.get_header(token=token)
        data = {"worldIds":world_ids,"chainId":op_chain_id}

        resp = None
        for i in range(try_times):
            try:
                resp = await self.http.post(url, headers=headers, json=data, proxies=self.proxies, timeout=timeout, impersonate="chrome")
                break
            except Exception as e:
                logger.error(f"{self.addr} : 获取探索签名异常:{e}")
                await self.switch_proxy()
                continue
        
        if resp is None:
            logger.error(f"{self.addr} : 获取探索签名完全失败:{e}")
            return False

        if resp.status_code != 201:
            logger.error(f"{self.addr} : 获取探索签名失败1:{resp.text}")
            return False

        resp_json = json.loads(resp.text)

        if not resp_json['success']:
            logger.error(f"{self.addr} : 获取探索签名失败2:{resp.text}")
            return False
        
        if "data" not in resp_json:
            logger.error(f"{self.addr} : 获取探索签名失败3: {resp.text}")
            return False
        
        sign = resp_json['data']

        # 调用合约
        gas_price = await self.web3.eth.gas_price
        mint_func = self.expore_contract.functions.explore(int(sign['deadline']), sign['voyageId'], sign['destinations'], sign['data'], sign['signature'])
        for i in range(try_times):
            try:
                if mint_func is None:
                    return False
                nonce = await self.web3.eth.get_transaction_count(self.account.address)
                tx = await mint_func.build_transaction({
                    'from': self.addr,
                    'chainId': op_chain_id,
                    'gas': gas_price,
                    'nonce': nonce,
                    'gas':0,
                    'maxFeePerGas': 18,
                    'maxPriorityFeePerGas': 2,
                })
                gas = int(await self.web3.eth.estimate_gas(tx))
                tx.update({'gas' : gas})

                tx_sign = self.account.sign_transaction(tx)
                tx_id = await self.web3.eth.send_raw_transaction(tx_sign.rawTransaction)
                receipt = await self.web3.eth.wait_for_transaction_receipt(tx_id)
                if receipt.status == 1:
                    logger.success(f"[{self.addr}] 探索上链成功 {tx_id.hex()} ")
                    is_succ = await self.check_explore(token, sign['voyageId'])
                    if is_succ:
                        logger.success(f"[{self.addr}] 探索完全成功 {tx_id.hex()} {sign['voyageId']}")
                        cache.set(cache_key, resp_json['data'], expire=get_today_expired())
                        return True
                    else:
                        logger.error(f"[{self.addr}] 探索完全失败 {tx_id.hex()} {sign['voyageId']}")
                        return False
                else:
                    logger.error(f"[{self.addr}] 探索任务失败1 {tx_id.hex()}")
                return False
            except Exception as e:
                logger.error(f"[{self.addr}] 探索任务失败2 {e}")
                await self.switch_proxy()
                continue

        logger.error(f"[{self.addr}] 探索完全失败2 {tx_id.hex()} {sign['voyageId']}")
        return False
    
    # 提交探索
    async def check_explore(self, token, id):
        url = f'https://pml.ultiverse.io/api/explore/check?id={id}&chainId={op_chain_id}'
        headers = self.get_header(token=token)
        for i in range(try_times):
            try:
                resp = await self.http.get(url, headers=headers, proxies=self.proxies, timeout=timeout, impersonate="chrome")
                if resp.status_code != 200:
                    logger.error(f"{self.addr} : check探索失败1:{resp.text}")
                    await self.switch_proxy()
                    continue

                resp_json = json.loads(resp.text)

                if not resp_json['success']:
                    logger.error(f"{self.addr} : check探索失败2:{resp.text}")
                    await self.switch_proxy()
                    continue
                
                if "data" not in resp_json:
                    logger.error(f"{self.addr} : check探索失败3: {resp.text}")
                    await self.switch_proxy()
                    continue

                return resp_json['data']['success']
            except Exception as e:
                logger.error(f"{self.addr} : 检查探索异常: {e}")
                await self.switch_proxy()
                continue
            
        logger.error(f"{self.addr} : 检查探索完全失败")
        return False
    
    # 切换代理
    async def switch_proxy(self):
        await asyncio.sleep(1)
        self.proxies = get_proxy()

    
async def run():
    # 打开文件并解析 JSON
    logger.add(f"/opt/logs/pilot.log", level="INFO")

    with open('wallet.json', 'r') as file:
        walletList = json.load(file)

    for k, w in enumerate(walletList):
        proxy = proxies_list[k]
        w['proxy'] = {
            'http': proxy,
            'https': proxy
        }
        walletList[k] = w

    stop_event = asyncio.Event()

    async def register(queue):
        ua_faker = fake_useragent.UserAgent(os='macos')
        while not stop_event.is_set():
            await asyncio.sleep(10)
            try:
                msg = await asyncio.wait_for(queue.get(), timeout=15)
                private = msg['private']
                address = msg['address']
                proxy = msg['proxy']
                ua = ua_faker.random

                p = Pilot(private, address, ua, proxies=proxy)

                token = await p.login()
                if not token:
                    logger.error(f"{address} 获取token失败")
                    continue
                is_succ = await p.invite(token)
                if not is_succ:
                    logger.error(f"{address} 邀请失败")
                    continue
                is_succ = await p.set_nick_name(token)
                if not is_succ:
                    logger.error(f"{address} 设置昵称失败")
                    continue
                is_succ = await p.mint(token=token)
                if not is_succ:
                    logger.error(f"{address} mint失败")
                    continue
                logger.success(f"{address} 注册成功")

            except asyncio.TimeoutError:
                logger.info(f"协程退出")
                break
            except Exception as e:
                logger.error(f"发生异常:{e} {traceback.format_exc()} {msg}")
                continue

    async def explore_run(queue):
        ua_faker = fake_useragent.UserAgent(os='macos')
        while not stop_event.is_set():
            try:
                msg = await asyncio.wait_for(queue.get(), timeout=15)
                private = msg['private']
                address = msg['address']
                proxy = msg['proxy']
                ua = ua_faker.random

                p = Pilot(private, address, ua, proxies=proxy)

                token = await p.login()
                if not token:
                    logger.error(f"{address} 获取token失败")
                    continue

                # 检查可探索的选项
                world_list = []
                try:
                    explore_list = await p.get_explore_list(token=token)
                    if not explore_list:
                        raise Exception("获取探索列表失败")
                    balance = await p.get_balance(token=token)
                    if not balance:
                        raise Exception("获取soul余额失败")
                    soul_balance = int(balance['soulInAccount'])
                    const = 0
                    for i in explore_list:
                        if not i['active']:
                            continue
                        if int(i['soul']) + const <= soul_balance:
                            const = const + int(i['soul'])
                            world_list.append(i['worldId'])
                except Exception as e:
                    logger.error(f"{address} 查看可做探索失败:{e}")
                    world_list = None

                is_succ = await p.explore(token=token, world_ids=world_list)
                if not is_succ:
                    logger.error(f"{address} 探索失败")
                    continue
                logger.success(f"{address} 探索成功")
                # await asyncio.sleep(10)

            except asyncio.TimeoutError:
                logger.info(f"协程退出")
                break
            except Exception as e:
                logger.error(f"发生异常:{e} {traceback.format_exc()} {msg}")
                continue


    
    # 开启协程
    tasks = []
    queue = asyncio.Queue()

    # ----------------- 探索任务执行这个 -----------------
    # task = asyncio.create_task(explore_run(queue))
    # ----------------- 注册任务执行这个 -----------------
    task = asyncio.create_task(register(queue))
    tasks.append(task)

    # 注册
    for w in walletList:
        for a in w["accountList"]:
            private = a['key']
            address = a['addr']
            proxy = w['proxy']

            await queue.put({
                "private" : private,
                "address" : address,
                "proxy" : proxy,
            })

    await asyncio.gather(*tasks)
            
            

if __name__ == '__main__':
    asyncio.run(run())
