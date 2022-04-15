# coding=utf-8

import yaml
import requests
import threading
import json
import logging
from country_emoji_data import get_country_map

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
        self.country_map = get_country_map()
        self.global_proxies_with_country_flags = {}

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
            logging.debug("Start thread: {}".format(t.name))
            t.start()

        for t in threads:
            t.join(timeout=5)
            logging.debug("End thread: {}".format(t.name))

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
            country_flag = self.global_proxies_with_country_flags.get(p_name)
            config = "  - {}\n".format(json.dumps(p, ensure_ascii=False))
            # generate server config with contry flag
            self.config += config.replace('{"name": "', '{"name": "' + country_flag)

        # write proxies name
        self.config += """\n\nproxy-groups:\n- name: V2\n  proxies:\n"""
        for n in self.proxies_name:
            country_flag = self.global_proxies_with_country_flags.get(n)
            # generate server name with country flag
            self.config += "  - \"{}{}\"\n".format(country_flag, n)

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

    # parse domain to ip with DOT DNS
    def _domain_to_ip(self, domain_or_ip):
        data = domain_or_ip.split(".")
        data_type = "ip"
        for i in data:
            if not i.isdigit():
                data_type = "domain"
                break

        if data_type == "domain":
            url = "https://dns.google/resolve?name=" + domain_or_ip
            r = requests.get(url)
            if r.status_code != 200:
                logging.error("HTTP:{} domain_or_ip: {} Resp:{}".format(r.status_code, domain_or_ip, r.text))
                return "1.1.1.1"

            resp = r.json().get("Answer")
            if resp:
                domain_or_ip = r.json().get("Answer")[0].get("data")
            else:
                domain_or_ip = "1.1.1.1"
            
            domain_or_ip = self._domain_to_ip(domain_or_ip)

        logging.debug("Final IP: {}".format(domain_or_ip))
        return domain_or_ip

    # get country code by batch
    def _iplist_to_country_code(self, ip_list):
        # remove duplicate ip
        ip_list = list(set(ip_list))

        # API receive max to 100 ip once
        url = "http://ip-api.com/batch"
        ip_to_country_code = {}

        for i in range(0, len(ip_list), 100):
            if i + 100 < len(ip_list):
                tmp_list = ip_list[i:i+100]
            else:
                tmp_list = ip_list[i:]

            r = requests.post(url, data=json.dumps(tmp_list))
            if r.status_code != 200:
                logging.debug(ip_list)
                logging.error("HTTP:{} Resp:{}".format(r.status_code, r.text))
            else:
                for i in r.json():
                    ip_to_country_code[i.get("query")] = i.get("countryCode")
        
        return ip_to_country_code

    # update global proxies to append the country flags
    def append_country_flags(self):
        domain_or_ip_list = list(map(lambda x: x.get("server"), self.global_proxies.values()))
        ip_list_map = {}
        for i in domain_or_ip_list:
            ip_list_map[i] = self._domain_to_ip(i)
        
        ip_list = list(ip_list_map.values())
        ip_to_country_code = self._iplist_to_country_code(ip_list)

        for item in list(self.global_proxies.values()):
            try:
                domain = item["server"]
                ip = ip_list_map[domain]
                country_code = ip_to_country_code[ip]
                self.global_proxies_with_country_flags[item["name"]] = self.country_map[country_code]
            except KeyError:
                logging.error("Key Error: {} {} {} {}".format(domain, ip, country_code, item["name"]))
                self.global_proxies_with_country_flags[item["name"]] = self.country_map["US"]


        logging.debug(self.global_proxies)


    def run(self):
        self.collect_proxy()
        self.clean_proxies()
        self.append_country_flags()
        self.export_proxy()
        self.upload_to_gist()


if __name__ == "__main__":
    v = Vmess()
    v.run()
