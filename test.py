from tqdm import tqdm
import time

total_steps = 5
with tqdm(total=total_steps, desc="Processing") as pbar:
    for i in range(total_steps):
        # Perform some processing here
        time.sleep(0.1)
        pbar.update(1)
        pbar.update(1)
        pbar.update(1)
        pbar.update(1)