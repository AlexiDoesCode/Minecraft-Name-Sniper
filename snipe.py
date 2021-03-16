from datetime import datetime
from os import path
from typing import List

import json
import aiohttp
import asyncio

import requests
from bs4 import BeautifulSoup

headers: dict = {
    "Content-Type": "application/json",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:83.0) Gecko/20100101 Firefox/83.0"

}


class Account:

    def __init__(self, email, password, *questions):
        self.session = None
        self.auth_headers = None
        self.email = email
        self.password = password
        self.questions = questions
        self.access_token = None
        self.ign = None
        self.uuid = None

    async def authenticate(self):
        data = {
            "agent": {
                "name": "Minecraft",
                "version": 1
            },
            "username": self.email,
            "password": self.password
        }
        async with self.session.post('https://authserver.mojang.com/authenticate', json=data,
                                     headers=headers) as response:
            auth = json.loads(await response.text())
            self.access_token = auth["accessToken"]
            self.ign = auth["selectedProfile"]['name']
            self.uuid = auth["selectedProfile"]['id']
            self.auth_headers = {"Authorization": f"Bearer {self.access_token}", "Content-Type": "application/json"}

            if response.status == 200:
                async with self.session.get("https://api.mojang.com/user/security/challenges",
                                            headers=self.auth_headers) as \
                        security_questions:
                    res = json.loads(await security_questions.text())
                    ids = []
                    if len(res) > 0:

                        if len(self.questions) == 3:

                            for question in res:
                                ids.append(question["answer"]["id"])

                            answers = [
                                {
                                    "id": ids[0],
                                    "answer": self.questions[0]
                                },
                                {
                                    "id": ids[1],
                                    "answer": self.questions[1]
                                },
                                {

                                    "id": ids[2],
                                    "answer": self.questions[2]
                                }
                            ]

                            async with self.session.post("https://api.mojang.com/user/security/location", json=answers,
                                                         headers=self.auth_headers) as answer:

                                if answer.status == 204:
                                    return True, self
                                else:
                                    return False, self

                        else:
                            return False, self
                    else:
                        return True, self
            else:
                return False, self

    async def change_name(self, name: str):

        current_time = datetime.now()
        async with self.session.put(f"https://api.minecraftservices.com/minecraft/profile/name/{name}",
                                    headers=self.auth_headers) as res:
            if res.status == 200:
                print("[SUCCESS] " + str(res.status) + " " + current_time.strftime("%d/%m/%y %H:%M:%S.%f"))
                return True, self
            else:
                print("[FAIL] " + str(res.status) + " " + current_time.strftime("%d/%m/%y %H:%M:%S.%f"))
                return False, self


def load_accounts() -> List[Account]:
    accounts: List[Account] = []

    if not path.exists("accounts.txt"):
        with open("accounts.txt", "w+") as _:
            pass

        return []

    else:
        with open("accounts.txt", "r") as f:
            combos = [a.strip() for a in f.readlines()]

    for combo in combos:
        combo = combo.split(':')

        if len(combo) in (3, 5):
            accounts.append(Account(*combo))

    return accounts


def get_drop_time(name: str) -> datetime:
    site = requests.get(f"https://namemc.com/{name}", headers=headers)
    soup = BeautifulSoup(site.text, 'html.parser')

    time = soup.find(id="availability-time")
    drop_time = time['datetime']
    dt = datetime.fromisoformat(drop_time[:-1])

    return dt


async def main():

    accounts: List[Account] = load_accounts()
    name = str(input("[INPUT] Pick the name you want to snipe: "))
    offset = float(input("[INPUT] Choose your delay: "))
    authenticated_accounts: List[Account] = []
    if len(accounts) == 0:
        print("No accounts found! D:")
        return

    async with aiohttp.ClientSession() as session:
        for account in accounts:
            account.session = session

        for result in await asyncio.gather(*[account.authenticate() for account in accounts]):
            if True in result:
                account = result[1]
                authenticated_accounts.append(account)
                print(f"[SUCCESS] Successfully authenticated {account.ign}")
            else:
                print("[FAIL] Failed to authenticate.")
        time_now = datetime.utcnow()

        time_until_drop = get_drop_time(name).timestamp() - time_now.timestamp()

        await asyncio.sleep(time_until_drop + offset / 1000)
        i = 2
        for result in await asyncio.gather(*[account.change_name(name) for account in authenticated_accounts for _ in
                                             range(i)]):
            if True in result:
                account = result[1]
                print(f"[SUCCESS] Successfully sniped the name {name} using the email {account.email}")
            else:
                print("[FAIL] Failed to snipe the name.")


if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
