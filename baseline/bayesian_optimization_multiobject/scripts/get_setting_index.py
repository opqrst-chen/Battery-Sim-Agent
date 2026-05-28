import yaml

setting_file_path = "../../generate_simulated_data/output/simulated_data_setting_single_new_filtered.yaml"
# setting_file_path = "../../generate_simulated_data/output/simulated_data_setting_multi_new_filtered.yaml"
with open(setting_file_path, "r", encoding="utf-8") as f:
    setting_data = yaml.safe_load(f)

setting_indexes = []
for index, setting in setting_data.items():
    setting_indexes.append(str(index))

setting_indexes = ' '.join(setting_indexes)
print(setting_indexes)