import logging
import os
import base64
import json
from jinja2 import Template
import yaml
import openai

from utils.exp import save_to_jsonl, get_configs,  extract_dict, gather_level_dicts

logger = logging.getLogger(__name__)

llm_configs = get_configs(config_type="llm", config_name="all")

_DEFAULT_PROMPT_PATH = os.path.normpath(
    os.path.join(os.path.dirname(os.path.abspath(__file__)), os.pardir, "prompt.yaml")
)

def get_prompt_template(prompt_name: str = "SYSTEM_PROMPT",
                        prompt_path: str = _DEFAULT_PROMPT_PATH):
    with open(prompt_path, 'r', encoding='utf-8') as file:
        prompt = yaml.safe_load(file)

    prompt_template = prompt.get(prompt_name, '')

    return prompt_template

def generate_first_cycle_message(current_params,
                                 cycle_description,
                                 image_path: str=None,
                                 protocols=None,
                                 cycle_idxs=None,
                                #  target_capacity: float=None,
                                #  simulated_capacity: float=None,
                                 parameter_set: str=None,
                                 model_name: str=None,
                                 multi_modal: bool = False,
                                 search_keys: list[str] = None,
                                 round_index: int = 0,
                                 prompt_type='FIRST_CYCLE_PROMPT'):
    # FIRST_CYCLE_PROMPT: FIRST_ROUND_PROMPT, TEXT_KNOWLEDGE, SEARCH_KNOWLEDGE, OTHER_ROUND_PROMPT
    # Get prompt setting
    cycle_prompt = get_prompt_template(prompt_name=prompt_type)

    prompt_config = llm_configs['PROMPT']

# PROMPT:
#   KNOWLEDGE: TEXT_KNOWLEDGE
#   WITH_FIGURE: true
#   WITH_DETAIL_DIFFERENCE: true
    print('round_index',round_index)
    if round_index == 1:
        template = Template(cycle_prompt['FIRST_ROUND_PROMPT'])

        if prompt_config['KNOWLEDGE']:
            knowledge_template = Template(cycle_prompt[prompt_config['KNOWLEDGE']])

        context = {
            "protocols": protocols,
            "current_params": current_params,
            "parameter_set": parameter_set,
            "model_name": model_name,
            # "target_capacity": target_capacity,
            # "simulated_capacity": simulated_capacity,
            "cycle_description": cycle_description,
            "search_keys": search_keys
        }
        if prompt_type == 'DEGREDATION_PROMPT':
            context['cycle_idxs'] = cycle_idxs
        first_round_prompt = template.render(context)
        text_knowledge     = knowledge_template.render(context)
        rendered_string = first_round_prompt + "\n" + text_knowledge

    else:
        template = Template(cycle_prompt['OTHER_ROUND_PROMPT'])
        context = {
            "cycle_description": cycle_description,
            "search_keys": search_keys
        }
        rendered_string = template.render(context)

    if multi_modal == False:
        messages = [{"role": "user", "content": rendered_string}]
    else:
        messages = [{
            "role":
            "user",
            "content": [{
                "type": "text",
                "text": rendered_string
            }]
        }]
        if image_path:
            messages[0]["content"].append({
                "type": "image_url",
                "image_url": {
                    "url": create_data_uri(image_path, "image/png")
                }
            })
    print(messages)
    # logger.info(f"[Info] LLM Messages: {messages}")
    return messages

def generate_degradation_message(real_data,
                                 sim_sol,
                                 params_to_search,
                                 index_to_search: list[int] = [1, 2, 3, 4, 5],
                                 capacity_jsonl_path: str = None):

    # Create a Template object
    template = Template(get_prompt_template(prompt_name="DEGREDATION_PROMPT"))

    context = {
        'total_cycle_number': 500,
        'current_params': params_to_search,
        'real_to_sim_plot': 'example_plot_url',
        'cycles': []
    }
    capacity_data = {}
    for idx, cycle_num in enumerate(index_to_search):
        real_index = index_to_search[idx]
        sim_index = index_to_search[idx]
        context['cycles'].append({
            'cycle_num':
            cycle_num,
            'real_index':
            real_index,
            'real_capacity':
            real_data['formatted_cycle_data'][f"cycle_{real_index}"]
            ['discharge_capacity_in_Ah'][-1],
            'sim_index':
            sim_index,
            'sim_capacity':
            sim_sol.cycles[sim_index]['Discharge capacity [A.h]'].entries[-1]
        })
        capacity_data[f"cycle_{real_index}"] = {
            'real_capacity':
            real_data['formatted_cycle_data'][f"cycle_{real_index}"]
            ['discharge_capacity_in_Ah'][-1],
            'sim_capacity':
            sim_sol.cycles[sim_index]['Discharge capacity [A.h]'].entries[-1]
        }

    save_to_jsonl(capacity_data, capacity_jsonl_path, mode="a")

    # Render the template with the context
    rendered_string = template.render(context)

    messages = [{"role": "user", "content": rendered_string}]
    # logger.info(f"[Info] LLM Messages: {messages}")
    return messages

def generate_multi_vote_message(llm_responses):
    # Create a Template object
    template = Template(
        get_prompt_template(prompt_name="MULTI_VOTE")["USER_PROMPT"])
    context = {"all_suggestions": llm_responses}
    rendered_string = template.render(context)
    multi_vote_messages = [{
        "role":
        "system",
        "content":
        get_prompt_template(prompt_name="MULTI_VOTE")["SYSTEM_PROMPT"]
    }, {
        "role": "user",
        "content": rendered_string
    }]
    return multi_vote_messages

def image_to_base64(image_path):
    with open(image_path, "rb") as image_file:
        encoded_string = base64.b64encode(image_file.read()).decode('utf-8')
        return encoded_string

def create_data_uri(image_path, mime_type):
    base64_string = image_to_base64(image_path)
    return f"data:{mime_type};base64,{base64_string}"

def call_llm(messages, response_format: str = "json_object"):
    assert response_format in [
        'guidance', 'json_object', 'text'
    ], "response_format must be one of ['guidance', 'json_object', 'text']"
    print('response_format', response_format)
    client = openai.OpenAI(base_url=llm_configs["BASE_URL"]
                           or os.getenv("OPENAI_BASE_URL"),
                           api_key=llm_configs["API_KEY"]
                           or os.getenv("OPENAI_API_KEY"))
    try:
        response = client.chat.completions.create(
            model=llm_configs["LLM_MODEL_NAME"],
            messages=messages,
            temperature=llm_configs["TEMPERATURE"],
            response_format={"type": response_format}
        )
        res = response.choices[0].message.content
        logger.info(f"[Info] response: {response}")
        logger.info(
            f"[Info] LLM Response: {response.choices[0].message.content}")
        return True, res

    except Exception as e:
        logger.error(f"Error calling LLM: {e}")
        return False, None

import re

def call_llm_for_params_to_update(mode: str,
                                  messages,
                                  multi_vote_number: int = 1,
                                  all_messages_jsonl_path: str = None,
                                  time_stamp=None,
                                  search_keys=None
                                ):
    logger.info(f"[Info] LLM Messages: {messages}")

    if mode == "first_cycle":
        llm_success, llm_response = call_llm(messages)
        if llm_success:
            save_to_jsonl({"llm_response_first_cycle": llm_response},
                          all_messages_jsonl_path,
                          mode="a")
            logger.info(f"[DEBUG]### LLM Response: {llm_response}")
            # params_to_update = get_params_from_response(llm_response)
            param_groups_list = gather_level_dicts(extract_dict(llm_response), search_keys)
            # params_to_update = get_first_cycle_params_from_response(
            #     llm_response)
            # filter group list
            param_groups_list = [{k: v for k, v in item.items() if k in search_keys} for item in param_groups_list]

            return llm_response, param_groups_list
        else:
            return None, None
    elif mode == "degradation":
        llm_response_list = []
        params_to_update_list = []
        for i in range(1, multi_vote_number + 1):
            llm_success, llm_response = call_llm(messages)
            if llm_success:
                save_to_jsonl(
                    {f"llm_response_multi_vote_index_{i}": llm_response},
                    all_messages_jsonl_path,
                    mode="a")
                llm_response_list.append(llm_response)
                llm_response_json = json.loads(llm_response)
                response_params_to_update = llm_response_json[
                    'params_to_update']
                params_to_update = {
                    param['name']: float(param['value'])
                    for param in response_params_to_update
                }
                params_to_update_list.append(params_to_update)
                logger.info(
                    f"[Info] Params to update - Multi_Vote_{i}: {params_to_update}"
                )
            else:
                logger.error(
                    f"[Error] LLM failed to generate params to update.")

        if multi_vote_number == 1:
            return llm_response_list[0], params_to_update_list[0]
        else:
            multi_vote_llm_response_list = {
                f"Multi_Vote_{i}": llm_response_list[i - 1]
                for i in range(1, multi_vote_number + 1)
            }
            multi_vote_messages = generate_multi_vote_message(
                llm_response_list)
            multi_vote_llm_success, multi_vote_llm_response = call_llm(
                multi_vote_messages)
            if multi_vote_llm_success:
                multi_vote_llm_response_json = json.loads(
                    multi_vote_llm_response)
                multi_vote_response_params_to_update = multi_vote_llm_response_json[
                    'params_to_update']
                multi_vote_params_to_update = {
                    param['name']: float(param['value'])
                    for param in multi_vote_response_params_to_update
                }
                # multi_vote_llm_response_list.update(
                #     {"multi_vote_llm_response": multi_vote_llm_response})
            save_to_jsonl({"multi_vote_llm_response": multi_vote_llm_response},
                          all_messages_jsonl_path,
                          mode="a")
            return multi_vote_llm_response, multi_vote_params_to_update

#####################################################################
############## from call api all params new.ipynb ###################
#####################################################################

def update_session(messages, new_input, input_type='user'):
    if 'img_url' in new_input.keys():
        content = [
            {
                "type": "image_url",
                "image_url": {
                    "url": new_input['img_url']
                }
            },
            {
                "type": "text",
                "text": new_input['text']
            },
        ]
    else:
        content = new_input['text']

    item = {
        "role": input_type,
        "content": content,
    }
    messages.append(item)
    return messages

import ast
import re

def get_params_from_response(response):
    pattern = r'updated_params\s*=\s*({.*?})\n\n'
    match = re.search(pattern, response, re.DOTALL)

    if match:
        dict_str = match.group(1)
        # Replace non-breaking spaces and other special characters with standard spaces
        dict_str = dict_str.replace('\xa0',
                                    ' ').replace('‑', '-').replace('–', '-')
        # Safely evaluate the string to a dictionary
        updated_params = ast.literal_eval(dict_str)
        # print(updated_params)
        return updated_params
    else:
        print("Dictionary not found in the text.")
        return None
    # # Extract the part of the string containing the dictionary
    # start = response.find("updated_params = {")
    # end = response.find("}", start) + 1
    # dict_str = response[start:end]
    # dict_str = dict_str.replace('\xa0', ' ').replace('‑', '-').replace('–', '-')
    # # Convert the string representation of the dictionary into an actual dictionary
    # updated_params = ast.literal_eval(dict_str.split('=', 1)[1].strip())

    # # Print the resulting dictionary
    # print(updated_params)

def get_first_cycle_params_from_response(llm_response):
    pattern = r'updated_params\s*=\s*({.*?})'
    match = re.search(pattern, llm_response, re.S)
    if match:
        dict_str = match.group(1)
        updated_params = ast.literal_eval(dict_str)
        print(updated_params)
    else:
        print("updated_params not found")
    return updated_params
