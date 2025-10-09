import os
import time
import copy
import asyncio
import threading
from typing import List
from llm_playground.core.baseagent import TaskAgent

from llm_playground.utils.helpers import write_base_model_items_to_json_array_file
from llm_playground.core.models import is_restricted_llm


class InferenceRunner(object):
    def __init__(
        self, agents: List[TaskAgent], output_dirpath: str, records, is_appending=False
    ):
        self.agents = agents
        self.output_dirpath = output_dirpath
        if not os.path.exists(self.output_dirpath):
            os.makedirs(self.output_dirpath)
        self.records = records
        self.is_appending = is_appending

    async def run_by_agent(
        self,
        agent: TaskAgent,
        output_json_array_filepath: str,
        max_batch_size: int,
        records,
    ):
        print(f"{agent.get_unique_label()} is running...")
        _start = time.time()

        OUTPUT_MODE = "w"
        if self.is_appending:
            OUTPUT_MODE = "a"

        # restricted llm condition
        if is_restricted_llm(agent.llm_name):
            fp = open(output_json_array_filepath, mode=OUTPUT_MODE, encoding="utf-8")
            fp.write("[\n")

            JSON_INDENT = 2
            cnt_total_records = len(records)

            if cnt_total_records <= 1:
                for idx, record in enumerate(records):
                    print(
                        f"{agent.get_unique_label()} running... ({idx + 1} of {cnt_total_records})"
                    )
                    new_record = await agent.async_process(record)
                    fp.write(
                        new_record.model_dump_json(
                            indent=JSON_INDENT,
                        )
                    )
                    fp.write("\n")
            else:
                for idx, record in enumerate(records[:-1]):
                    print(
                        f"{agent.get_unique_label()} running... ({idx + 1} of {cnt_total_records})"
                    )
                    new_record = await agent.async_process(record)
                    fp.write(
                        new_record.model_dump_json(
                            indent=JSON_INDENT,
                        )
                    )
                    fp.write(",\n")
                    fp.flush()

                print(
                    f"{agent.get_unique_label()} running... ({cnt_total_records} of {cnt_total_records})"
                )
                new_record = await agent.async_process(records[-1])
                fp.write(
                    new_record.model_dump_json(
                        indent=JSON_INDENT,
                    )
                )
                fp.write("\n")

            fp.write("]\n")
            fp.close()
        else:
            new_records = await agent.async_process_multiple(
                records=records, max_batch_size=max_batch_size
            )

            write_base_model_items_to_json_array_file(
                output_json_array_filepath, new_records, uid_filtering=False
            )

        print(
            f"{agent.get_unique_label()} is completed, elapse {time.time() - _start} seconds."
        )

    def run_by_agent_thread(
        self,
        agent: TaskAgent,
        output_json_array_filepath: str,
        max_batch_size: int,
        records,
    ):
        asyncio.run(
            self.run_by_agent(
                agent, output_json_array_filepath, max_batch_size, records
            )
        )

    def run_in_sequence(self, max_batch_size: int = 64):
        for agent in self.agents:
            output_json_array_filepath = os.path.join(
                self.output_dirpath, f"{agent.get_unique_label()}.json"
            )
            asyncio.run(
                self.run_by_agent(
                    agent, output_json_array_filepath, max_batch_size, self.records
                )
            )

    def run_in_multithread(self, max_batch_size: int = 64):
        threads = []
        for agent in self.agents:
            output_json_array_filepath = os.path.join(
                self.output_dirpath, f"{agent.get_unique_label()}.json"
            )
            # 这里 records 参数在 process 函数中会被修改然后返回
            # 因此这里需要深拷贝一份 records, 再传入每个线程中进行执行

            records = copy.deepcopy(self.records)

            t = threading.Thread(
                target=self.run_by_agent_thread,
                args=(agent, output_json_array_filepath, max_batch_size, records),
            )
            t.start()
            threads.append(t)
        for t in threads:
            t.join()
