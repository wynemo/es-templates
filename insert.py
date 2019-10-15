import os
import glob


from elasticsearch import helpers, NotFoundError
from elasticsearch_dsl.connections import connections


import os
import json
from hashlib import md5


def load_json(each):
    with open(each, 'r', encoding='utf-8') as f:
        each = os.path.basename(each)
        if each.startswith('N_'):
            each = each.replace('N_', '')  #
            device_type = '网络设备'
        elif each.startswith('P_'):
            each = each.replace('P_', '')  # 安全防护
            device_type = '安全防护'
        elif each.startswith('S_'):
            each = each.replace('S_', '')  # 应用服务
            device_type = '应用服务'
        else:
            device_type = '其他'
        each = each.replace('.json', '')

        o = json.load(f)
        if o.get('results'):
            data = o['results']
        if o.get('data'):
            data = o['data']
        for entity in data:
            entity['county'] = entity.pop('location.country', None) or entity.pop('country_name', None) or ''
            entity['city'] = entity.pop('location.city', None) or entity.pop('city', None) or ''
            entity['ip'] = entity.get('ip') or ''
            entity['port'] = entity.get('port') or ''
            results = each.split('_', maxsplit=1)
            if len(results) == 2:
                vendor, product = results
            else:
                vendor, product = each, each
            entity['vendor'] = vendor
            entity['product'] = product
            entity['device_type'] = device_type

            rv = {"_op_type": 'update', "_index": 'some-index', "doc": entity, "doc_as_upsert": True,
                  '_id': md5(str(entity).encode()).hexdigest()}

            yield rv

def _write_es(path):
    settings = {"default":{"hosts":[{"host":"127.0.0.1","port":9200}],"max_retries":0,"timeout":120}}
    connections.configure(**settings)

    request_body = {
        "settings": {
        },

        'mappings': {
            'properties': {
                'county': {'type': 'keyword'},
                'city': {'type': 'keyword'},
                'vendor': {'type': 'keyword'},
                'product': {'type': 'keyword'},
                'device_type': {'type': 'keyword'},
            }}
    }
    es = connections.get_connection()
    index_name = 'some-index'
    try:
        es.indices.get(index=index_name)
        es.indices.delete(index=index_name)
    except NotFoundError:
        pass
    es.indices.create(index=index_name, body=request_body)

    for each in glob.glob(os.path.join(path, '*.json')):
        try:
            helpers.bulk(connections.get_connection(), load_json(each), index=index_name)
        except Exception as e:
            print(f'{each} insert failed {e}')
            continue

