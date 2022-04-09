# coding=utf-8

import yaml
import requests
import threading
import json
import logging

logging.basicConfig(format='%(asctime)s %(levelname)s:%(message)s', level=logging.DEBUG)
config = {}

with open("config.json", "r") as f:
    body = f.read()
    config = json.loads(body)


class Vmess(object):
    def __init__(self):
        self.start_url = config.get("subscribe_list")
        self.export_path = config.get("export_path")
        self.gist = config.get("gist")
        self.proxies = []
        self.proxies_name = []
        self.config = ""
        self.global_proxies = {}

    def parse_proxy(self, url):
        header = {
            "User-Agent": config.get("user_agent")
        }
        try:
            r = requests.get(url, headers=header)
            data = yaml.safe_load(r.text)
            for p in data.get("proxies"):
                self.proxies.append(p)
        except Exception as e:
            logging.error("Parse failed: {} Detail:".format(url, e))

    def collect_proxy(self):
        threads = [threading.Thread(target=self.parse_proxy, args=(url,)) for url in self.start_url]
        for t in threads:
            logging.debug("Start thread: {}".format(t.native_id))
            t.start()

        for t in threads:
            t.join(timeout=5)
            logging.debug("End thread: {}".format(t.native_id))

    @staticmethod
    def import_config_index():
        with open("config_template_start.yaml", "r") as f:
            return f.read()

    @staticmethod
    def import_config_end():
        with open("config_template_end.yaml", "r") as f:
            return f.read()

    def clean_proxies(self):
        for p in self.proxies:
            p_name = p.get("name").replace("\t", "")
            p["name"] = p_name
            self.global_proxies[p_name] = p

    def export_proxy(self):
        # write index
        self.config = self.import_config_index()

        # write proxies
        for p_name in sorted(self.global_proxies.keys()):
            p = self.global_proxies[p_name]
            self.proxies_name.append(p_name)
            self.config += "  - {}\n".format(json.dumps(p, ensure_ascii=False))

        # write proxies name
        self.config += """\n\nproxy-groups:\n- name: AUTO\n  proxies:\n"""
        for n in self.proxies_name:
            self.config += "  - \"{}\"\n".format(n)

        # write end
        self.config += self.import_config_end()

        with open(self.export_path, "w") as f:
            f.write(self.config)

    # upload to gist for subscribe
    def upload_to_gist(self):
        if self.gist.get("id") is None or self.gist.get("id") == "": return

        logging.info("Upload to gist...")
        url = "https://api.github.com/gists/" + self.gist.get("id")

        payload = json.dumps({
          "description": "clash",
          "public": True,
          "files": {
            "clash.yaml": {
              "content": self.config
            }
          }
        })
        headers = {
          'Accept': 'application/vnd.github.v3+json',
          'Authorization': 'Basic ' + self.gist.get("token"),
          'Content-Type': 'application/json'
        }

        response = requests.request("PATCH", url, headers=headers, data=payload)
        logging.debug(response.status_code)


    def run(self):
        self.collect_proxy()
        self.clean_proxies()
        self.export_proxy()
        self.upload_to_gist()


if __name__ == "__main__":
    v = Vmess()
    v.run()
