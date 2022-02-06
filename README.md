# Clash Subscribe Integration

## Description
To merge multiple Clash Subscription to one clash config. This Python script will do follow actions:
1. Download content from subscription
2. Parser proxies and generate proxies names
3. Generate finally clash config with template automatically
4. Finally config = template_start + (this export content) + template_end

## Usage
1. Edit `config.json`
2. Config explain:
```json
{
  "user_agent": "ClashX Pro", // your user agent that send to subscripion servers
  "export_path": "~/clash/config.yaml", // your output directory with config name
  "subscribe_list": [ // your subscriptions links
      "https://your_clash_subscribe_link_here.dev"
  ]
}
```

3. Run `python3 main.py`

## License
This software is released under the GPL-3.0 license.