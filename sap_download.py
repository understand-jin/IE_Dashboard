from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys  # ← 이거 추가
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
from datetime import datetime, timedelta
import time
import shutil
import glob
import os
import schedule
from webdriver_manager.chrome import ChromeDriverManager




def download_PO(save_dir=None):
    DEFAULT_DIR = r"C:\Users\USER\Desktop\IE Dashboard\input_data\ZMMR0210"
    download_dir = save_dir if save_dir else DEFAULT_DIR
    os.makedirs(download_dir, exist_ok=True)

    options = webdriver.ChromeOptions()
    options.add_experimental_option("prefs", {
    "download.default_directory": download_dir,
    "download.prompt_for_download": False,
})

    SAP_URL = "https://dspwp.sap.daewoong.com/sap/bc/ui2/flp?sap-client=100"
    SAP_ID = "3220407"
    SAP_PW = "Scmtlswlgjs0102&&"
    # SAP_ID = "2600144"
    # SAP_PW = "Ok3008@202011185@"

    today = datetime.today().strftime("%m.%d")
    SAVE_PATH = os.path.join(download_dir, f"ZMMR0210.xlsx")

    # driver = webdriver.Chrome(
    #     service=Service(r"C:\Users\USER\Downloads\chromedriver-win64\chromedriver-win64\chromedriver.exe"),
    #     options=options
    # )
    import os as _os
    _os.environ['WDM_SSL_VERIFY'] = '0'
    driver = webdriver.Chrome(
        service=Service(ChromeDriverManager().install()),
        options=options
    )
    wait = WebDriverWait(driver, 30)

    try:
         # ① 기존 파일 먼저 삭제 (다운로드 전에!)
        existing_files = glob.glob(os.path.join(download_dir, "*.xlsx"))
        for f in existing_files:
            os.remove(f)
            print(f"🗑️ 기존 파일 삭제: {f}")
        # ① 로그인
        driver.get(SAP_URL)
        wait.until(EC.presence_of_element_located((By.ID, "USERNAME_FIELD-inner")))
        driver.find_element(By.ID, "USERNAME_FIELD-inner").send_keys(SAP_ID)
        driver.find_element(By.ID, "PASSWORD_FIELD-inner").send_keys(SAP_PW)
        driver.find_element(By.ID, "LOGIN_LINK").click()
        #driver.save_screenshot("01_로그인완료.png")
        print("✅ 로그인 완료")

        # 검색 버튼 클릭
        wait.until(EC.element_to_be_clickable((By.ID, "sf")))
        driver.find_element(By.ID, "sf").click()
        time.sleep(0.5)

        # 검색창에 입력
        search_input = wait.until(EC.presence_of_element_located((By.ID, "searchFieldInShell-input-inner")))
        search_input.send_keys("ZMMR0210")
        search_input.send_keys(Keys.RETURN)
        print("✅ 검색 완료")

        time.sleep(3)

        # ② 메뉴 이동
        wait.until(EC.element_to_be_clickable((By.XPATH, "//*[contains(text(), '구매오더 진척현황 리포트')]")))
        driver.find_element(By.XPATH, "//*[contains(text(), '구매오더 진척현황 리포트')]").click()
        #driver.save_screenshot("02_메뉴이동완료.png")
        print("✅ 메뉴 이동 완료")

        # 새 창 전환
        time.sleep(3)
        driver.switch_to.window(driver.window_handles[-1])
        print("✅ 새 창 전환 완료")

        # iframe 전환
        try:
            wait.until(EC.frame_to_be_available_and_switch_to_it((By.TAG_NAME, "iframe")))
            print("✅ iframe 전환 완료")
        except:
            print("ℹ️ iframe 없음, 계속 진행")


        # 올해 1월 1일 계산
        year_start = f"{datetime.today().year - 1}0101"  # 예: 20250101
        print(f"올해 시작일: {year_start}")

        # 증빙일 시작 필드 입력
        date_field = driver.find_element(By.CSS_SELECTOR, "input[title='구매 증빙일']")
        date_field.click()
        date_field.clear()
        for char in year_start:
            date_field.send_keys(char)
            time.sleep(0.1)
        date_field.send_keys(Keys.TAB)
        print(f"✅ 증빙일 입력 완료: {year_start}")

        # 페이지 안정화 대기 (중요!)
        time.sleep(2)

        plant_fields = driver.find_elements(By.CSS_SELECTOR, "input[title='플랜트']")
        plant_fields[0].clear()
        plant_fields[0].send_keys("1210")
        plant_fields[0].send_keys(Keys.TAB)

        plant_fields[1].clear()
        plant_fields[1].send_keys("1340")
        plant_fields[1].send_keys(Keys.TAB)
        print("✅ 플랜트 입력 완료 (1210 ~ 1340)")

        time.sleep(2)

        # 회사 코드 비우기
        company_field = driver.find_element(By.CSS_SELECTOR, "input[title='회사 코드']")
        company_field.clear()
        company_field.send_keys(Keys.TAB)

        # 구매 조직 비우기
        org_field = driver.find_element(By.CSS_SELECTOR, "input[title='구매 조직']")
        org_field.clear()
        org_field.send_keys(Keys.TAB)
        print("✅ 회사 코드 / 구매 조직 초기화 완료")

        time.sleep(2)

        # 외자 라디오버튼 클릭
        wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "[aria-label='외자']")))
        driver.find_element(By.CSS_SELECTOR, "[aria-label='외자']").click()
        print("✅ 외자 선택 완료")

        time.sleep(2)

        # 일반 라디오버튼 클릭
        wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "[aria-label='일반']")))
        driver.find_element(By.CSS_SELECTOR, "[aria-label='일반']").click()
        print("✅ 일반 선택 완료")

        time.sleep(2)
        # 방법 2 - F8 키 직접
        ActionChains(driver).send_keys(Keys.F8).perform()
        print("✅ F8 실행 완료")

        # # 결과 로딩 대기 (중요!)
        # time.sleep(20)

        # # 엑스포트 버튼 클릭
        # wait.until(EC.element_to_be_clickable((By.ID, "_MB_EXPORT111")))
        # driver.find_element(By.ID, "_MB_EXPORT111").click()
        # print("✅ 엑스포트 메뉴 열림")
        # time.sleep(2)

        time.sleep(10)
        # 엑스포트 버튼 클릭
        wait.until(EC.element_to_be_clickable((By.ID, "_MB_EXPORT104")))
        driver.find_element(By.ID, "_MB_EXPORT104").click()
        print("✅ 엑스포트 메뉴 열림")
        time.sleep(2)

        # 스프레드시트 클릭
        try:
            wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "tr[aria-label='스프레드시트']")))
            driver.find_element(By.CSS_SELECTOR, "tr[aria-label='스프레드시트']").click()
            print("✅ 스프레드시트 선택 완료 (방법1)")
        except:
            try:
                wait.until(EC.element_to_be_clickable((By.XPATH, "//*[contains(text(), '스프레드시트')]")))
                driver.find_element(By.XPATH, "//*[contains(text(), '스프레드시트')]").click()
                print("✅ 스프레드시트 선택 완료 (방법2)")
            except:
                wait.until(EC.element_to_be_clickable((By.ID, "menu_MB_EXPORT104_1_1")))
                driver.find_element(By.ID, "menu_MB_EXPORT104_1_1").click()
                print("✅ 스프레드시트 선택 완료 (방법3)")

        # 엑스포트 버튼 클릭
        wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "[title='데이터 엑스포트 (Shift+F8)']")))
        driver.find_element(By.CSS_SELECTOR, "[title='데이터 엑스포트 (Shift+F8)']").click()
        print("✅ 엑스포트 클릭 완료")

        # 확인 버튼 클릭
        wait.until(EC.element_to_be_clickable((By.ID, "UpDownDialogChoose")))
        driver.find_element(By.ID, "UpDownDialogChoose").click()
        time.sleep(3)
        print("✅ 다운로드 완료")

    except Exception as e:
        driver.save_screenshot("error_캡처.png")
        print(f"❌ 에러 발생: {e}")

    finally:
        # 다운로드 완료 대기 (최대 30초)
        for _ in range(30):
            files = glob.glob(os.path.join(download_dir, "*.xlsx"))
            crdownload = glob.glob(os.path.join(download_dir, "*.crdownload"))
            if files and not crdownload:
                break
            time.sleep(1)

        # 다운로드된 파일을 원하는 이름으로 변경
        files = glob.glob(os.path.join(download_dir, "*.xlsx"))
        latest_file = max(files, key=os.path.getctime)
        os.rename(latest_file, SAVE_PATH)
        print(f"✅ 파일 저장 완료: {SAVE_PATH}")

        driver.quit()

download_PO()

#download_inventory_overview()

# def job():
#     print("🕘 자동 실행 시작!")
#     download_sap_data()

# # 매일 오전 9시 실행
# schedule.every().day.at("09:00").do(job)

# print("✅ 스케줄러 시작 - 매일 09:00 실행")
# while True:
#     schedule.run_pending()
#     time.sleep(60)