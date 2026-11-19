SCHEDULE_DB = {
    "550e8400-e29b-41d4-a716-446655440000": [
        True, False, True, True, False, False, True, True, False, True
    ],
    "7c9e6679-7425-40de-944b-e07fc1f90ae7": [
        False, True, True, False, True, True, False, False, True, False
    ],
    "550e5600-e29b-41d4-a716-446655440000": [
            False, True, True, False, True, True, False, False, True, False
        ],
}

SALES_DB = {
    "550e8400-e29b-41d4-a716-446655440000": {
        "periods": [15000, None, 18500, 14000, None, None, 20000, 16500, None, 13000],
        "total": 97000
    },
    "7c9e6679-7425-40de-944b-e07fc1f90ae7": {
        "periods": [None, 8000, 9500, None, 11000, 7500, None, None, 12000, None],
        "total": 48000
    },
    "550e5600-e29b-41d4-a716-446655440000": {
            "periods": [15000, None, 18500, 14000, None, None, 20000, 16500, None, 13000],
            "total": 103000
        }
}

#for id, data in SALES_DB.items():
#    print(SALES_DB[id]["total"])

a = 3200
b = 3000

c = int(round(a/b*100))

print(c)


for id, data in SALES_DB.items():
    print(sum(SCHEDULE_DB[id]))