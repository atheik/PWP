import json
import requests
from re import match

API_URL = "http://localhost:5000"

def prompt_from_body(body):
    """
    Print menu using contents from the request body.
    Prompt to select from available collection items as well as actions and validate user input.
    Return the appropriate control, depending on whether the resource is a collection or an item.
    """
    item_choices = 0
    try:
        body["items"]
    except KeyError:
        print("{:-^80}".format(" Item "))
        props = body.copy()
        del props["@namespaces"]
        del props["@controls"]
        if props:
            print(props)
    else:
        print("{:-^80}".format(" Collection "))
        for item in body["items"]:
            item_choices += 1
            item_props = item.copy()
            del item_props["@controls"]
            print(item_choices, item_props)

    choices = item_choices
    print("{:-^80}".format(" Actions "))
    for ctrl in body["@controls"]:
        choices += 1
        print(choices, ctrl)

    pick = 0
    while pick < 1 or pick > choices:
        print("{:-^80}".format(" Prompt "))
        pick = input("Pick " + ("an item or " if item_choices else "") + "an action (number): ")
        try:
            pick = int(pick)
        except ValueError:
            pick = 0
    
    if pick > item_choices:
        ctrl = list(body["@controls"].values())[pick - item_choices - 1]
    else:
        ctrl = body["items"][pick - 1]["@controls"]["self"]
    return ctrl

def prompt_from_schema(ctrl):
    """
    Prompt to enter properties according to schema and validate user input.
    Return the built request control and data.
    """
    schema = ctrl["schema"]
    properties = schema["properties"]
    required = schema["required"]

    i = 0
    req_data = {}
    while i < len(properties):
        prop = list(properties.keys())[i]

        print("{:-^80}".format(" Prompt "))
        req_data[prop] = input(properties[prop]["description"] + " (" + ("required" if prop in required else "optional") + "): ")

        if req_data[prop]:
            prop_type = properties[prop]["type"]
            if prop_type.lower() == "integer":
                try:
                    req_data[prop] = int(req_data[prop])
                except ValueError:
                    continue

            try:
                prop_pattern = properties[prop]["pattern"]
            except KeyError:
                pass
            else:
                if not match(prop_pattern, req_data[prop]):
                    continue
        elif prop in required:
            continue
        else:
            del req_data[prop]

        i += 1

    req_ctrl = {"method": ctrl["method"], "href": ctrl["href"]}
    return req_ctrl, req_data

def submit_data(s, ctrl, data):
    """
    Send a PUT or POST request, depending on the control.
    Request data is serialized to JSON and the Content-Type is set accordingly.
    Return the response.
    """
    resp = s.request(
        ctrl["method"],
        API_URL + ctrl["href"],
        data=json.dumps(data),
        headers={"Content-Type": "application/json"}
    )
    return resp

def handle_action(s, ctrl):
    """
    Derive request method from the control and perform the request.
    With schema available, the method is assummed to be either PUT or POST and the user is prompted to input data.
    On error, print the Mason error message.
    """
    try:
        ctrl["schema"]
    except KeyError:
        pass
    else:
        req_ctrl, req_data = prompt_from_schema(ctrl)
        resp = submit_data(s, req_ctrl, req_data)
        try:
            resp.raise_for_status()
        except requests.HTTPError:
            body = resp.json()
            print("{:*^80}".format(" Error response "))
            print(*body["@error"]["@messages"])
        else:
            print("{:*^80}".format(" Ok response "))

    try:
        ctrl["method"]
    except KeyError:
        pass
    else:
        if ctrl["method"].lower() == "delete":
            resp = s.delete(API_URL + ctrl["href"])
            try:
                resp.raise_for_status()
            except requests.HTTPError:
                body = resp.json()
                print("{:*^80}".format(" Error response "))
                print(*body["@error"]["@messages"])
            else:
                print("{:*^80}".format(" Ok response "))

"""
"""
if __name__ == "__main__":
    try:
        print("Press the interrupt key (normally Control-C or Delete) to exit")
        with requests.Session() as s:
            href = prev_href = "/api/"
            while True:
                resp = s.get(API_URL + href)
                try:
                    resp.raise_for_status()
                except requests.HTTPError:
                    href = prev_href
                    continue

                print("{:=^80}".format(" " + href + " "))

                try:
                    body = resp.json()
                except ValueError:
                    print("{:*^80}".format(" Text response "))
                    print(resp.text)
                    href = prev_href
                    continue

                ctrl = prompt_from_body(body)
                handle_action(s, ctrl)

                if href != ctrl["href"]:
                    prev_href = href
                    href = ctrl["href"]
    except KeyboardInterrupt:
        pass
