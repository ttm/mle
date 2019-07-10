from pylab import *
from bregman.suite import *
import sys
import music as m

fname = sys.argv[1]
nc = int(sys.argv[2])
npath = os.environ['nuxtPATH']
npath_ = npath + 'static/audio/'
fname_ = npath_ + fname

import AudioSpectrumPatchApproximation as A # 2D spectrogram patch sparse approximation library
F = LogFrequencySpectrum(fname_, nhop=1024, nfft=8192, wfft=4096, npo=24) # constant-Q transform
pargs = {'normalize':True, 'dbscale':True, 'cmap':cm.hot, 'vmax':0, 'vmin':-45} # plot arguments

s3 = A.SparseApproxSpectrumPLCA2D(patch_size=(12,8)) # Same idea as above, but with non-negative components
s3.extract_codes(F, n_components=nc, log_amplitude=True, alphaW=0.0, alphaZ=0.0, alphaH=0.0, betaW=0.00, betaZ=0.001, betaH=0.00)
# s3.plot_codes(cbar=True, cmap=cm.hot)


s3.reconstruct_individual_spectra()
# s3.plot_individual_spectra(**pargs)
# figure()
# subplot(211); feature_plot(F.X, nofig=True, **pargs); title('Original Spectrogram', fontsize=14)
# subplot(212); feature_plot(s3.X_hat, nofig=True, **pargs); title('Sparse Approximation', fontsize=14)


# In[98]:

ii = 0
fname__ = fname.replace('MMMEXCERPT.wav', 'MMMCOMPONENT')
for i in s3.X_hat_l:
    x_hat = F.inverse(i)
    m.core.W(x_hat, npath_ + '%s%d.wav' % (fname__, ii))
    ii += 1
