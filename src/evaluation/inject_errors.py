import pandas as pd
import random

def inject_errors(df):

    df_dirty = df.copy()

    # error 1: nulos
    idx = random.sample(range(len(df)), 5)
    df_dirty.loc[idx, "edad"] = None

    # error 2: valores negativos
    idx = random.sample(range(len(df)), 3)
    df_dirty.loc[idx, "precio"] = -10

    # error 3: duplicados
    df_dirty = pd.concat([df_dirty, df_dirty.sample(2)])

    return df_dirty