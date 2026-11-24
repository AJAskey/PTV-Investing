import talib

def calc_swing(price, mode):
    return 0
    
def price_to_ma(price, ma):
    return (price - ma) / ma

def highest(highs,period):
    tab
    ret = 0.0
    iret= 0
    len1 = len(highs)
    if period > len1:
        return 0,0
    len = max(len1,period)
    for i in range(1,len):
        if highs[i] > ret:
            ret = highs[i]
            iret = i
    return ret,iret

def lowest(lows,period):
    ret = []
    for i in range(len(lows)):
        ret.append(min(lows[i-period:i+1]))
    return ret

def ma_direction(ma):
    direction = [0]
    for i in range(1, len(ma)):
        if ma[i] > ma[i-1]:
            direction.append(1)
        else:
            direction.append(-1)
    return direction

def force(close,volume,period):
    if len(close) < period:
        return 0 
    if len(volume) < period:
        return 0
    if period < 1:
        return 0
    vma = talib.SMA(volume, timeperiod=period)

    f = 0.0
    av = vma[-1]
    # print(f'{av=:.2f}')
    for i in range(1,period-1):
        d = ((close[i] - close[i+1])/close[i+1]) if close[i+1] !=0 else 0
        f1 = d * volume[i]
        f += f1
        # print(f'{i=} {close[i]=:.2f} {close[i+1]=:.2f} {d=:.4f}, {volume[i]=:.0f}, {f1=:.2f}, {f=:.2f}')
    if av != 0:
        ret=f/av
    else:
        ret=0
    # print(f'{ret=:.2f}')
    return ret

      

if __name__ == "__main__":
    print("Hello World")    
    price = 22.5
    ma20 = 20
    ma50 = 25
    print(f"{price_to_ma(price, ma20):.2f}%")
    print(f"{price_to_ma(price, ma50):.2f}%")
