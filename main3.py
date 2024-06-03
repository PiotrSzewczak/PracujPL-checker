import requests
from bs4 import BeautifulSoup
import json
import http.client
import urllib.parse
import schedule
import time

saved_job_listings = []
# Konfiguracja Pushover
PUSHOVER_API_TOKEN = "azyxyqsjrb7qox673hc2b7c6jv23gv"
PUSHOVER_USER_KEY = "u98etrot15kvoqzx4gu32pvurup1fh"

# URL strony z ogłoszeniami
url = "https://it.pracuj.pl/praca/warszawa;wp?rd=30&et=1%2C3%2C17"

# Funkcja do pobrania listy ogłoszeń
def fetch_job_listings(url):
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'}
        response = requests.get(url, headers=headers)
        response.raise_for_status()  # Dodaj obsługę błędów HTTP
        soup = BeautifulSoup(response.content, 'html.parser')

        # Znajdź element <script> zawierający dane JSON
        script_tag = soup.find('script', {'id': '__NEXT_DATA__', 'type': 'application/json'})
        if not script_tag:
            return []

        # Pobierz i sparsuj dane JSON
        data = json.loads(script_tag.string)

        # Wyciągnij oferty pracy z danych JSON
        job_offers = data['props']['pageProps']['data']['jobOffers']['groupedOffers']

        job_listings = []
        for offer in job_offers:
            job = {
                'id': offer['offers'][0].get('offerAbsoluteUri', 'Brak linku'),  # Użycie linku jako unikalnego ID
                'title': offer.get('jobTitle', 'Brak tytułu'),
                'company': offer.get('companyName', 'Brak firmy'),
                'location': offer['offers'][0].get('displayWorkplace', 'Brak lokalizacji'),
                'link': offer['offers'][0].get('offerAbsoluteUri', 'Brak linku'),
                'description': offer.get('jobDescription', 'Brak opisu'),
                'salary': offer.get('salaryDisplayText', 'Brak wynagrodzenia')
            }
            job_listings.append(job)

        return job_listings
    except Exception as e:
        print(f"Error fetching job listings: {e}")
        return []

# Funkcja do wysyłania powiadomień przez Pushover
def send_pushover_notification(message, title):
    try:
        params = {
            "token": PUSHOVER_API_TOKEN,
            "user": PUSHOVER_USER_KEY,
            "message": message,
            "title": title,
        }
        headers = { "Content-type": "application/x-www-form-urlencoded" }
        conn = http.client.HTTPSConnection("api.pushover.net:443")
        conn.request("POST", "/1/messages.json", urllib.parse.urlencode(params), headers)
        response = conn.getresponse()
        print(response.status, response.reason)
        if response.status != 200:
            print(response.read().decode())  # Wyświetl szczegółową odpowiedź serwera w przypadku błędu
    except Exception as e:
        print(f"Error sending notification: {e}")

# Funkcja sprawdzająca ogłoszenia i wysyłająca powiadomienia
def check_and_notify():
    global saved_job_listings
    job_listings = fetch_job_listings(url)
    for job in job_listings:
        title = "Praca: " + job['title']
        opis = job['description']
        opis = opis.replace("Twój zakres obowiązków, ", '')
        opis = opis.replace("Your responsibilities, ", '')
        message = f"Tytuł: {job['title']}\nFirma: {job['company']}\nLokalizacja: {job['location']}\nLink: {job['link']}\nOpis: {opis}\nWynagrodzenie: {job['salary']}"
        send_pushover_notification(message, title)
        saved_job_listings.append(job['id'])

# Cykliczne sprawdzanie co minutę
schedule.every().minute.do(check_and_notify)

# Sprawdź, czy program został uruchomiony po raz pierwszy
first_run = True
# Pętla główna programu
while True:
    schedule.run_pending()
    if first_run:
        send_pushover_notification("To jest pierwsza wiadomość do sprawdzenia skryptu", "TEST")
        initial_listings = fetch_job_listings(url)
        saved_job_listings.extend(job['id'] for job in initial_listings)
        first_run = False
    time.sleep(10)
