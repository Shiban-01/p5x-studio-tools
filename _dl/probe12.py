import wave, array, hashlib, math
def rd(p):
    with wave.open(p,"rb") as f:
        ch=f.getnchannels(); sw=f.getsampwidth(); fr=f.getframerate()
        n=f.getnframes(); d=f.readframes(n)
    a=array.array("h"); a.frombytes(d)
    return ch,sw,fr,a
import sys
ja=rd(r"C:/Users/Lukas/p5x-datamining/_dl/_tmp_hash/p3r_ja.wav")
ch=rd(r"C:/Users/Lukas/p5x-datamining/_dl/_tmp_hash/p3r_ch.wav")
print("ja:", ja[:3], "len",len(ja[3]))
print("ch:", ch[:3], "len",len(ch[3]))
def rms(a):
    if not a: return 0
    return (sum(x*x for x in a)/len(a))**0.5
print("RMS ja=%.1f ch=%.1f" % (rms(ja[3]), rms(ch[3])))
n=min(len(ja[3]),len(ch[3]))
diff=[ja[3][i]-ch[3][i] for i in range(n)]
print("RMS(ja-ch)=%.1f" % rms(diff))
# FFT flatness via numpy if available
try:
    import numpy as np
    for name,a in (("ja",ja[3]),("ch",ch[3]),("ja-ch",diff)):
        x=np.frombuffer(array.array("h",a).tobytes(),dtype=np.int16).astype(np.float64)
        # mono downmix
        x=x[:len(x)//2*2]; x=(x[0::2]+x[1::2])/2
        seg=min(len(x),48000*20)
        X=np.abs(np.fft.rfft(x[:seg]*np.hanning(seg)))
        X=X[X>0]
        print("  flatness %-6s = %.4f (n=%d)" % (name, float(np.exp(np.mean(np.log(X)))/np.mean(X)), seg))
except Exception as e:
    print("numpy no:", e)
