"""Exact constant(a,omega) unicycle interval and analytic sensitivities.

The integral's convergent series is evaluated to order12; with |omega*dt|<=.04,
the omitted terms are below double precision. No v/omega division or small-turn
singularity is introduced. State0 is fixed; controls parameterize hard dynamics.
"""
import math
import numpy as np
DT=.1;N=25

def step(state,control,h=DT):
    x,y,theta,v=map(float,state);a,w=map(float,control);z=1j*w*h
    powers=np.asarray([z**n/math.factorial(n) for n in range(13)])
    A=[h**(m+1)*sum(powers[n]/(n+m+1) for n in range(13)) for m in range(3)]
    rot=np.exp(1j*theta);delta=rot*(v*A[0]+a*A[1])
    result=np.array([x+delta.real,y+delta.imag,theta+w*h,v+a*h])
    fx=np.eye(4);fx[:2,2]=[(-delta.imag),delta.real];q=rot*A[0];fx[:2,3]=[q.real,q.imag]
    fu=np.zeros((4,2));q=rot*A[1];fu[:2,0]=[q.real,q.imag];q=1j*rot*(v*A[1]+a*A[2]);fu[:2,1]=[q.real,q.imag]
    fu[2,1]=h;fu[3,0]=h
    return result,fx,fu

def trajectory(initial,controls):
    u=np.asarray(controls,float).reshape(N,2);states=np.empty((N+1,4));states[0]=initial
    jac=np.zeros((N+1,4,2*N))
    for k in range(N):
        states[k+1],fx,fu=step(states[k],u[k]);jac[k+1]=fx@jac[k];jac[k+1,:,2*k:2*k+2]+=fu
    return states,jac
