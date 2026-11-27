ptv_path = "C:/Dev/PTV-Investing/"
stockdata_path = f"{ptv_path}/stockdata"
subdata_path = f"{ptv_path}/subs"

def dict_to_str(dik, desc=""):
    out_str = desc + "\n"
    for key, value in dik.items():
        out_str += f"  {key} | {value}\n"
    return out_str
