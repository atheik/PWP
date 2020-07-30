import json
import requests
from re import match

API_URL = "http://localhost:5000"

def submit_data(s, ctrl, data):
    """
    TODO
    """
    resp = s.request(
        ctrl["method"],
        API_URL + ctrl["href"],
        data=json.dumps(data),
        headers = {"Content-type": "application/json"}
    )
    return resp

def prompt_from_schema(s, ctrl):
    """
    TODO
    """
    schema = ctrl["schema"]
    properties = schema["properties"]
    required = schema["required"]

    req_data = {}
    for prop in required:
        print(80 * "-")
        req_data[prop] = input(properties[prop]["description"] + ": ")

        prop_type = properties[prop]["type"]
        if prop_type == "integer":
            try:
                req_data[prop] = int(req_data[prop])
            except ValueError:
                required.insert(0, prop)
                continue

        try:
            prop_pattern = properties[prop]["pattern"]
        except KeyError:
            pass
        else:
            if not match(prop_pattern, req_data[prop]):
                required.insert(0, prop)
                continue

    req_ctrl = {"method": ctrl["method"], "href": ctrl["href"]}
    return req_ctrl, req_data

if __name__ == "__main__":
    href = prev_href = "/api/"
    while True:
        with requests.Session() as s:
            """
            TODO split this into a few functions
            """

            resp = s.get(API_URL + href)
            try:
                resp.raise_for_status()
            except requests.HTTPError:
                href = prev_href
                continue

            try:
                body = resp.json()
            except ValueError:
                print(80 * "=")
                print(resp.text)
                href = prev_href
                continue

            item_choices = 0
            try:
                body["items"]
            except KeyError:
                print(80 * "=")
                props = body.copy()
                del props["@namespaces"]
                del props["@controls"]
                print(props)
            else:
                print(80 * "=")
                for item in body["items"]:
                    item_choices += 1
                    item_props = item.copy()
                    del item_props["@controls"]
                    print(item_choices, item_props)

            choices = item_choices
            print(80 * "-")
            for ctrl in body["@controls"]:
                choices += 1
                print(choices, ctrl)

            pick = 0
            while pick < 1 or pick > choices:
                print(80 * "-")
                subprompt = "an item or action" if item_choices else "an action"
                pick = input("Pick {} (number): ".format(subprompt))

                try:
                    pick = int(pick)
                except ValueError:
                    pick = 0
            
            if pick > item_choices:
                ctrl = list(body["@controls"].values())[pick - item_choices - 1]
            else:
                ctrl = body["items"][pick - 1]["@controls"]["self"]

            try:
                ctrl["schema"]
            except KeyError:
                pass
            else:
                req_ctrl, req_data = prompt_from_schema(s, ctrl)
                resp = submit_data(s, req_ctrl, req_data)
                try:
                    resp.raise_for_status()
                except requests.HTTPError:
                    pass

            if ctrl["href"] != href:
                prev_href = href
            href = ctrl["href"]
