import numpy as np
import torch
from scipy.special import comb as nChoosek
Mtk = lambda i, n, t: (t**(i))*((1-t)**(n-i))*nChoosek(n,i)
def pinv(A):
    """
    Return the pseudoinverse of A,
    without invoking the SVD in torch.pinverse().
    """
    batch, rows, cols = A.size()
    if rows >= cols:
        Q,R = torch.qr(A)
        return torch.matmul(R.inverse(),Q.transpose(1,2))
    else:
        Q,R = torch.qr(A.transpose(1,2))
        return torch.matmul(R.inverse(),Q.transpose(1,2)).transpose(1,2)
       # return R.inverse().mm(Q.transpose(1,2)).transpose(1,2)
def bezierM(t,n):
    # M = torch.zeros(t.shape[0],t.shape[1],n+1).type_as(t)
    # for j in range(M.shape[0]):
    #     M[j]=torch.stack([Mtk(i,n,t[j]) for i in range(n+1)],dim=1)
    # return M
    return torch.stack([Mtk(i,n,t) for i in range(n+1)],dim=2)
def evalBezier(M,control_points):
    return torch.matmul(M,control_points)
def bezierDerivative(control_points,n,t):
    Mderiv = bezierM(t,n-1)
    pdiff =  control_points[:,1:] - control_points[:,:-1]
    return n*torch.matmul(Mderiv, pdiff)
def bezierLsqfit(points,t, n):
    M = bezierM(t,n)
    return M, torch.matmul(pinv(M), points)