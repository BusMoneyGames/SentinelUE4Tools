# SentinelConfig

TODO:

Handles generating a config from the environment in a structure like this

```javascript
{
	"ue4": {
			"engine":{},
			"project": {}
			"commandlets": {},
			"asset_types": {},
			"build_configs": {},
			"project_build_config": {}
	},
	"vcs": {
		commit_id:{},
		submodules:{},
		"changes": {}
	},
	"environment": {
		"project_root": {},
		"config_root": {},
		"vcs_root": {},
		"artifact_root": {}
		"cache_root": {}
		"engine_root": {}
		"custom_run_name": {}
	}
	"sentinel_iternal": {
		"logs": {}
		"processed": {}
		"builds": ""

	}
}
```
