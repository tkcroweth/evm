from eth_account import Account
import json
import datetime

# 启用助记词功能
Account.enable_unaudited_hdwallet_features()

""" 生成助记词账户
    num_mnemonics 钱包数量
    num_accounts_per_mnemonic 每个钱包的账户数量
    num_words 助记词长度
"""
def generate_mnemonics_with_accounts(num_mnemonics, num_accounts_per_mnemonic, num_words=12):
    mnemonics_with_accounts = []

    for _ in range(num_mnemonics):
        account, mnemonic = Account.create_with_mnemonic(num_words=num_words)

        accounts = []
        iterator = 0
        for _ in range(num_accounts_per_mnemonic):
            acct = Account.from_mnemonic(
                mnemonic,
                account_path=f"m/44'/60'/0'/0/{iterator}"
            )
            iterator += 1
            accounts.append(acct)

        mnemonics_with_accounts.append((mnemonic, accounts))

    return mnemonics_with_accounts

# # 助记词数量
# num_mnemonics = 1000
# # 每个助记词钱包数量
# num_accounts_per_mnemonic = 1
# # 助记词个数
# num_words_per_mnemonic = 12
# # 助记词保存路径
# file_dir = "./"

# 助记词数量
num_mnemonics = 0
while True:
    try:
        num_mnemonics = input("输入生成钱包的数量:").strip()
        if num_mnemonics:
            num_mnemonics = int(num_mnemonics)
            break
    except:
        continue

# 每个助记词钱包数量
num_accounts_per_mnemonic = input("输入每个钱包的账户数量(默认1):").strip()
if not num_accounts_per_mnemonic:
    num_accounts_per_mnemonic = 1
else:
    num_accounts_per_mnemonic = int(num_accounts_per_mnemonic)

# 助记词个数
num_words_per_mnemonic = 12
# 助记词保存路径
file_dir = "./"

# 生成钱包和助记词
generated_mnemonics_with_accounts = generate_mnemonics_with_accounts(num_mnemonics, num_accounts_per_mnemonic, num_words_per_mnemonic)

walletList = []

csv_info = ""
for i, (mnemonic, accounts) in enumerate(generated_mnemonics_with_accounts):
    item = {}
    item["mnemonic"] = mnemonic
    accountList = []
    for _, account in enumerate(accounts):
        accountList.append({
            "addr" : account.address,
            "key" : account.key.hex(),
        })

    csv_info = csv_info + f"{mnemonic},{account.address},{account.key.hex()}\n"
    item["accountList"] = accountList
    walletList.append(item)

# 获取当前日期和时间，并格式化为字符串
date_str = datetime.datetime.now().strftime("%Y%m%d%H%M")

# 写入csv
filename = f"{file_dir}wallet_{date_str}.csv"
with open(filename, 'w') as file:
    file.write(csv_info)

# 写入json
filename = f"{file_dir}wallet_{date_str}.json"
with open(filename, 'w') as file:
    json.dump(walletList, file)
