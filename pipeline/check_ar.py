import json

data = json.load(open('layout_5p_6f_9x16.json', encoding='utf-8'))
ars = []
bad = []
for page in data['pages']:
    for p in page['panels']:
        ar = p['aspect_ratio']
        ars.append(ar)
        if ar < 0.56 or ar > 2.20:
            bad.append((p['global_order'], ar, p['aspect_label']))

print(f'Tong khung: {len(ars)}')
print(f'AR min: {min(ars):.4f}  max: {max(ars):.4f}')
print()
for page in data['pages']:
    for p in page['panels']:
        ar = p['aspect_ratio']
        flag = ' <-- VI PHAM' if ar < 0.56 or ar > 2.20 else ''
        print(f'  Khung #{p["global_order"]:02d}: AR={ar:.4f} ({p["aspect_label"]}){flag}')

print()
if bad:
    print(f'CANH BAO: {len(bad)} khung vi pham [0.56, 2.20]')
else:
    print('OK - Tat ca khung trong gioi han [0.56, 2.20]')
