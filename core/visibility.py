import jax
from jaxoplanet.experimental.starry.wigner import dot_rotation_matrix
from jaxoplanet.experimental.starry.rotation import Rdot
import jax.numpy as jnp
from .utils import get_ylm_FTs
from scipy.special import jn as besselj
from jax import config

from .solution import transform_to_zernike, nm_to_j, j_to_nm, jmax, zernike_FT, CHSH_FT, A
from scipy.special import factorial2
from scipy.special import jv, spherical_jn
import numpy as np

config.update("jax_enable_x64", True)


jax_funcs = get_ylm_FTs()
def analytic_v(l_max,u,v,inc,obl,theta,y):
    rho = jnp.sqrt(u**2 + v**2)
    phi = jnp.arctan2(v,u)
    
    #start with y, do Rdot (not dotR) for each step in v except in regular order (read from top down in order)
    #end with rotated y
    #apply solution matrix at left to rotated y inside a for loop or the like
    x = Rdot(l_max, jnp.array([1.0, 0.0, 0.0]))(y,0.5 * jnp.pi)
    x = Rdot(l_max, jnp.array([0, 0, 1.0]))(x,theta)
    x = Rdot(l_max, jnp.array([1.0, 0.0, 0.0]))(x,-0.5 * jnp.pi)
    x = Rdot(l_max, jnp.array([0, 0, 1.0]))(x,obl)
    x = Rdot(
    l_max, jnp.array([-jnp.cos(obl), -jnp.sin(obl), 0.0]))(x,-(0.5 * jnp.pi - inc))
    
    ft = np.zeros_like(rho)
    y_hsh = []
    for l in range(l_max+1):
        for m in range(-l,l+1):
            #HSH
            if (l+m)%2==0:
                y_hsh.append(x[l**2+l+m])
            else:
                ft += CHSH_FT(l,m)(rho,phi)*x[l**2+l+m]
    y_hsh = np.array(y_hsh)
    print(len(y_hsh))
    zs = transform_to_zernike(y_hsh)
    for j in range(len(zs)):
        n,m = j_to_nm(j)
        ft += zs[j]*zernike_FT(n,m)(rho,phi)
    return ft
        
    
    
def v(l_max, u,v,inc,obl,theta, y):
    """
    Computes the visibility function for a given spherical harmonic map
    represented using the spherical harmonic coefficient vector y.
    Rotates the star to an orientation on sky given by inclination (inc)
    obliquity (obl), and theta (phase). The visibility function returns 

    Args:
        u (float): _description_
        v (float): _description_
        inc (float): _description_
        obl (float): _description_
        theta (float): _description_
        y (array): _description_
    """
    rho = jnp.sqrt(u**2 + v**2)
    phi = jnp.arctan2(v,u)
    nmax = l_max**2 + 2 * l_max + 1
    fT = []
    for l in range(l_max+1):
        for m in range(-l,l+1):
            fT.append(eval(jax_funcs[(l,m)]))
    fT = jnp.array(fT).T
    
    #read from bottom to top to understand in order:
    
    #now rotate by the inclination, making sure to perform it along the original y axis (hence the cos and sin of obliquity)
    x = dot_rotation_matrix(
    l_max, -jnp.cos(obl), -jnp.sin(obl), 0.0, -(0.5 * jnp.pi - inc)
    )(fT)
    #rotate to the correct obliquity
    x = dot_rotation_matrix(l_max, None, None, 1.0, obl)(x)
    #rotate back to the equator-on view
    x = dot_rotation_matrix(l_max, 1.0, 0.0, 0.0, -0.5 * jnp.pi)(x)
    #rotate by theta to the correct phase, this is done for speed?
    x = dot_rotation_matrix(l_max, None, None, 1.0, theta)(x)
    #first rotate about the x axis 90 degrees so the vector pointing at the observer is now the pole
    x = dot_rotation_matrix(l_max, 1.0, 0.0, 0.0, 0.5 * jnp.pi)(x)

    return x @ y
    
    
    
    
    