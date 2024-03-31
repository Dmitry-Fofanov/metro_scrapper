import csv

import requests

API_URL = 'https://api.metro-cc.ru/products-api/graph'
BASE_URL = 'https://online.metro-cc.ru'
MAX_RETRIES = 5
BACKOFF_FACTOR = 0.1

STORE_ID = 10
ITEMS_PER_REQUEST = 30
CATEGORY = 'chay'

TSV_HEADERS = (
    'ID',
    'Name',
    'URL',
    'Regular Price, RUB',
    'Sale Price, RUB',
    'Brand Name',
)


class ShopItem:
    def __init__(self, item_dict):
        self.id = item_dict['id']
        self.name = item_dict['name']
        self.url = BASE_URL + item_dict['url']
        prices = item_dict['stocks'][0]['prices']
        if prices['is_promo']:
            self.regular_price = prices['old_price']
            self.sale_price = prices['price']
        else:
            self.regular_price = prices['price']
            self.sale_price = None
        self.brand = item_dict['manufacturer']['name']

    def to_dict(self):
        return {
            'id':            self.id,
            'name':          self.name,
            'url':           self.url,
            'regular_price': self.regular_price,
            'sale_price':    self.sale_price,
            'brand':         self.brand,
        }

    def to_list(self):
        return [
            self.id,
            self.name,
            self.url,
            self.regular_price,
            self.sale_price,
            self.brand,
        ]


def retrieve_data(url, request_body):
    with requests.Session() as session:
        session.mount(
            'https://',
            requests.adapters.HTTPAdapter(
                max_retries=requests.adapters.Retry(
                    total=MAX_RETRIES,
                    backoff_factor=BACKOFF_FACTOR,
                ),
            ),
        )

        recieved = ITEMS_PER_REQUEST
        while recieved == ITEMS_PER_REQUEST:
            try:
                response = session.post(url=API_URL, json=request_body)
            except requests.exceptions.RetryError:
                break

            data = response.json()['data']['category']['products']
            data = [ShopItem(item).to_list() for item in data]

            recieved = len(data)
            request_body['variables']['from'] += ITEMS_PER_REQUEST

            yield data


if __name__ == '__main__':
    request_body = {
        'query': '',
        'variables': {
            'isShouldFetchOnlyProducts': True,
            'slug': CATEGORY,
            'storeId': STORE_ID,
            'sort': 'default',
            'size': ITEMS_PER_REQUEST,
            'from': 0,
            'filters': [
                {
                    'field': 'main_article',
                    'value': '0',
                },
            ],
            'attributes': [],
            'in_stock': True,
            'eshop_order': False,
        },
    }

    with open('query.txt') as file:
        request_body['query'] = file.read()

    with open(f'{CATEGORY}_results.tsv', 'w') as file:
        writer = csv.writer(file, delimiter='\t')
        writer.writerow(TSV_HEADERS)

        for batch in retrieve_data(API_URL, request_body):
            writer.writerows(batch)
