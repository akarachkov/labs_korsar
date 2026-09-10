"""Lab 006: exact slab solution and processing of exported KORSAR temperatures.

Run from the laboratory folder, see ../readme.md. CSV uses time_s,x_m,T_K.
No KORSAR results are generated or simulated by this script.
"""
from __future__ import annotations

import argparse
import csv
import json
import math
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
erfc = np.vectorize(math.erfc, otypes=[float])
integrate = np.trapezoid if hasattr(np, 'trapezoid') else np.trapz

DEFAULT = dict(L_m=0.02, area_m2=1.0, lambda_W_mK=16.0,
               rho_kg_m3=7800.0, cp_J_kgK=500.0, T0_K=293.15,
               Tb_K=393.15, step_time_s=1.0, boundary='dirichlet')
PROFILE_FO = np.array([0.0001, 0.001, 0.01, 0.05, 0.1, 0.3, 1., 2.])
PROBES = np.array([0.1, 0.25, 0.5, 0.75, 1.])


def validate_config(c):
    for key in ('L_m', 'area_m2', 'lambda_W_mK', 'rho_kg_m3', 'cp_J_kgK'):
        if not np.isfinite(c[key]) or c[key] <= 0:
            raise ValueError(f'{key} must be finite and positive')
    for key in ('T0_K', 'Tb_K', 'step_time_s'):
        if not np.isfinite(c[key]):
            raise ValueError(f'{key} must be finite')
    if min(c['T0_K'], c['Tb_K']) <= 0 or c['T0_K'] == c['Tb_K']:
        raise ValueError('Temperatures must be positive kelvin and different')
    if c['step_time_s'] < 0 or c['boundary'] not in ('dirichlet', 'insulated'):
        raise ValueError('Invalid step_time_s or boundary')


def scales(c):
    a = c['lambda_W_mK'] / (c['rho_kg_m3'] * c['cp_J_kgK'])
    tc = c['L_m'] ** 2 / a
    return tc, c['lambda_W_mK'] * (c['Tb_K'] - c['T0_K']) / c['L_m']


def eigenvalues(fo, boundary, tol):
    # Exponential tail bound with margin for both temperature and gradient.
    n = max(12, int(np.ceil(np.sqrt(np.log(100 / tol) / fo) / np.pi)) + 2)
    if n > 20000:
        raise ValueError('Fo too small for the requested Fourier-series tolerance')
    return np.pi * (np.arange(1, n + 1) - (0.5 if boundary == 'insulated' else 0))


def fourier_solution(x, fo, boundary='dirichlet', tol=1e-12):
    """Independent series representation, fo>0. Return theta and psi=-dtheta/dX."""
    mu = eigenvalues(fo, boundary, tol)
    expo = np.exp(-mu ** 2 * fo)
    angles = np.outer(mu, np.atleast_1d(x))
    steady = 1.0 if boundary == 'insulated' else 1 - np.atleast_1d(x)
    theta = steady - (2 * expo / mu) @ np.sin(angles)
    psi = (0.0 if boundary == 'insulated' else 1.0) + 2 * expo @ np.cos(angles)
    return theta, psi


def image_solution(x, fo, boundary='dirichlet', tol=1e-12):
    """Image/erfc representation; avoids cancellation near the cold face at small Fo."""
    x = np.atleast_1d(x)
    m = np.arange(int(np.ceil(np.sqrt(fo * np.log(100 / tol)))) + 3)[:, None]
    left, right = 2 * m + x, 2 * m + 2 - x
    z = 2 * np.sqrt(fo)
    if boundary == 'dirichlet':
        theta = np.sum(erfc(left / z) - erfc(right / z), axis=0)
        psi = np.sum(np.exp(-(left/z)**2) + np.exp(-(right/z)**2), axis=0)
    else:
        sign = (-1.0) ** m
        theta = np.sum(sign * (erfc(left / z) + erfc(right / z)), axis=0)
        psi = np.sum(sign * (np.exp(-(left/z)**2) - np.exp(-(right/z)**2)), axis=0)
    return theta, psi / np.sqrt(np.pi * fo)


def exact(x, fo, boundary='dirichlet', tol=1e-12):
    """Dimensionless theta=(T-T0)/(Tb-T0), psi=q*L/(lambda*(Tb-T0)).

    x is an array of X=x/L; Fo=0 means the right-hand limit after the step.
    At X=0, Fo=0 temperature is 1 and the heat flux is +infinity.
    """
    x = np.atleast_1d(np.asarray(x, dtype=float))
    if (not np.all(np.isfinite(x)) or np.any((x < 0) | (x > 1))
            or not np.isfinite(fo) or fo < 0):
        raise ValueError('Require 0<=X<=1 and finite Fo>=0')
    if boundary not in ('dirichlet', 'insulated'):
        raise ValueError('Unknown boundary')
    if not 0 < tol < 1e-3:
        raise ValueError('Require 0<tol<1e-3')
    if fo == 0:
        return (x == 0).astype(float), np.where(x == 0, np.inf, 0.)
    theta, psi = (image_solution if fo < 0.05 else fourier_solution)(x, fo, boundary, tol)
    theta[x == 0] = 1.
    if boundary == 'dirichlet':
        theta[x == 1] = 0.
    else:
        psi[x == 1] = 0.
    return theta, psi


def mean_theta(fo, boundary='dirichlet'):
    if fo == 0:
        return 0.
    mu = eigenvalues(fo, boundary, 1e-12)
    e = np.exp(-mu ** 2 * fo)
    if boundary == 'insulated':
        return 1 - np.sum(2 * e / mu ** 2)
    return .5 - np.sum(4 * e[::2] / mu[::2] ** 2)


def write_csv(path, rows):
    if not rows:
        return
    with path.open('w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def savefig(fig, path):
    fig.tight_layout()
    fig.savefig(path, dpi=170)
    plt.close(fig)


def make_reference(c, out):
    tc, qs = scales(c)
    x = np.linspace(0, 1, 301)
    rows = []
    fig, axes = plt.subplots(1, 2, figsize=(12, 5))
    ax = axes[0]
    for fo in PROFILE_FO:
        theta, psi = exact(x, fo, c['boundary'])
        ax.plot(x, theta, label=f'Fo={fo:g}')
        axes[1].plot(x*c['L_m']*1000, c['T0_K']+theta*(c['Tb_K']-c['T0_K'])-273.15, label=f'Fo={fo:g}')
        for xx, th, ps in zip(x, theta, psi):
            rows.append(dict(Fo=fo, X=xx, time_s=c['step_time_s'] + fo*tc,
                             x_m=xx*c['L_m'], theta=th, T_K=c['T0_K']+th*(c['Tb_K']-c['T0_K']),
                             psi=ps, q_W_m2=ps*qs, power_W=ps*qs*c['area_m2']))
    ax.set(xlabel='X = x/L', ylabel='theta = (T - T0)/(Tb - T0)', title=f'Analytical profiles: {c["boundary"]}')
    ax.grid(alpha=.3); ax.legend(ncol=2)
    axes[1].set(xlabel='x, mm', ylabel='T, deg C', title='Analytical temperature profiles')
    axes[1].grid(alpha=.3); axes[1].legend(ncol=2)
    savefig(fig, out/'temperature_profiles.svg')
    write_csv(out/'analytical_profiles.csv', rows)
    fos = np.geomspace(1e-5, 2, 350)
    values = np.array([exact(PROBES, fo, c['boundary'])[0] for fo in fos])
    fig, ax = plt.subplots(figsize=(8, 5))
    for j, xx in enumerate(PROBES):
        ax.semilogx(fos, values[:, j], label=f'X={xx:g}')
    ax.set(xlabel='Fo', ylabel='theta', title='Analytical temperature histories')
    ax.grid(alpha=.3); ax.legend(); savefig(fig, out/'temperature_histories.svg')
    flux = np.array([exact([0, 1], fo, c['boundary'])[1] for fo in fos])
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.4))
    for j, lab in enumerate(['x=0: inward', 'x=L: outward']):
        axes[0].semilogx(fos, flux[:, j], label=lab)
        axes[1].semilogx(fos*tc, flux[:, j]*qs, label=lab)
    axes[0].set(xlabel='Fo', ylabel='psi'); axes[1].set(xlabel='t - step time, s', ylabel='q, W/m2')
    axes[0].set_yscale('symlog', linthresh=.01)
    axes[1].set_yscale('symlog', linthresh=abs(qs)*.01)
    for ax in axes: ax.grid(alpha=.3); ax.legend()
    savefig(fig, out/'heat_flux.svg')
    write_csv(out/'analytical_history.csv', [dict(Fo=fo, time_s=c['step_time_s']+fo*tc,
        psi_left=f[0], psi_right=f[1], q_left_W_m2=f[0]*qs, q_right_W_m2=f[1]*qs,
        mean_theta=mean_theta(fo, c['boundary'])) for fo, f in zip(fos, flux)])


def read_run(path, c):
    data = np.genfromtxt(path, delimiter=',', names=True, encoding='utf-8-sig')
    data = np.atleast_1d(data)
    if not {'time_s', 'x_m', 'T_K'} <= set(data.dtype.names or ()):
        raise ValueError(f'{path}: expected time_s,x_m,T_K')
    if len(data) == 0 or any(not np.all(np.isfinite(data[k])) for k in ('time_s','x_m','T_K')):
        raise ValueError(f'{path}: empty or nonfinite data')
    if np.any(data['time_s'] < 0) or np.any(data['T_K'] <= 0):
        raise ValueError(f'{path}: negative time or invalid kelvin temperature')
    groups, previous_x = [], None
    for time in np.unique(data['time_s']):
        part = np.sort(data[data['time_s'] == time], order='x_m')
        x, temp = part['x_m'], part['T_K']
        if len(x) < 3 or np.any(np.diff(x) <= 0):
            raise ValueError(f'{path}: duplicate nodes or fewer than 3 nodes at t={time}')
        if abs(x[0]) > 1e-10 or abs(x[-1]-c['L_m']) > 1e-10:
            raise ValueError(f'{path}: export must include both surface nodes at 0 and L')
        if previous_x is not None and not np.array_equal(x, previous_x):
            raise ValueError(f'{path}: different spatial grids at different times')
        previous_x = x
        groups.append((time, x, temp))
    return groups


def process_runs(manifest, c, out, fo_min):
    tc, qs = scales(c)
    runs = json.loads(manifest.read_text(encoding='utf-8-sig'))
    if not isinstance(runs, list) or not runs:
        raise ValueError('Cases file must be a nonempty JSON list')
    metrics, summary, profile_rows = [], [], []
    labels = set()
    fig, axes = plt.subplots(1, 3, figsize=(14, 4.5))
    for run_index, run in enumerate(runs, 1):
        label = str(run['label'])
        if label in labels: raise ValueError('Case labels must be unique')
        labels.add(label)
        dt = float(run['dt_max_s'])
        if not np.isfinite(dt) or dt <= 0: raise ValueError('dt_max_s must be positive')
        groups = read_run(manifest.parent/run['csv'], c)
        runrows, prof = [], []
        for time, x, temp in groups:
            fo = (time-c['step_time_s'])/tc
            if fo <= 0: continue  # No finite surface flux exists at the jump itself.
            X = x/c['L_m']
            theta = (temp-c['T0_K'])/(c['Tb_K']-c['T0_K'])
            th_ref, _ = exact(X, fo, c['boundary'])
            # Second-order, three-point one-sided derivatives; handles unequal spacing.
            q = -c['lambda_W_mK'] * np.gradient(temp, x, edge_order=2)[[0, -1]]
            q_first = -c['lambda_W_mK'] * np.array([(temp[1]-temp[0])/(x[1]-x[0]),
                (temp[-1]-temp[-2])/(x[-1]-x[-2])])
            _, psi_ref = exact([0,1], fo, c['boundary'])
            # Apply the same spatial stencil to the exact profile to isolate recovery error.
            psi_stencil = -np.gradient(th_ref, X, edge_order=2)[[0,-1]]
            err = theta-th_ref
            row = dict(label=label, K=len(x), dt_max_s=dt, time_s=time, Fo=fo,
                eT_max=float(np.max(np.abs(err))), eT_L2=float(np.sqrt(integrate(err**2, X))),
                q_left_W_m2=q[0], q_right_W_m2=q[1],
                q_left_first_W_m2=q_first[0], q_right_first_W_m2=q_first[1],
                q_left_ref_W_m2=psi_ref[0]*qs, q_right_ref_W_m2=psi_ref[1]*qs,
                epsi_left=abs(q[0]/qs-psi_ref[0]), epsi_right=abs(q[1]/qs-psi_ref[1]),
                epsi_recovery_left=abs(psi_stencil[0]-psi_ref[0]),
                epsi_recovery_right=abs(psi_stencil[1]-psi_ref[1]),
                energy_J=c['rho_kg_m3']*c['cp_J_kgK']*c['area_m2']*integrate(temp-c['T0_K'],x),
                energy_ref_J=c['rho_kg_m3']*c['cp_J_kgK']*c['area_m2']*c['L_m']*(c['Tb_K']-c['T0_K'])*mean_theta(fo,c['boundary']))
            runrows.append(row); prof.append((fo,X,theta,th_ref))
        if not runrows: raise ValueError(f'{label}: no samples after step_time_s')
        # Integral balance between successive positive times; never integrate from singular t=0.
        for j, row in enumerate(runrows):
            row['interval_balance_J'] = np.nan
            if j:
                prev=runrows[j-1]
                transfer=.5*c['area_m2']*(row['time_s']-prev['time_s'])*(row['q_left_W_m2']-row['q_right_W_m2']+prev['q_left_W_m2']-prev['q_right_W_m2'])
                row['interval_balance_J']=row['energy_J']-prev['energy_J']-transfer
        use=[r for r in runrows if r['Fo'] >= fo_min]
        if not use: raise ValueError(f'{label}: no samples in Fo >= {fo_min}')
        summary.append(dict(label=label,K=use[0]['K'],dt_max_s=dt,Fo_first=use[0]['Fo'],Fo_last=use[-1]['Fo'],samples=len(use),
            max_eT=max(r['eT_max'] for r in use),max_epsi_left=max(r['epsi_left'] for r in use),
            max_epsi_right=max(r['epsi_right'] for r in use)))
        metrics.extend(runrows)
        fos=np.array([r['Fo'] for r in runrows])
        for ax,key in zip(axes,['eT_max','epsi_left','epsi_right']):
            ax.loglog(fos, np.maximum([r[key] for r in runrows],1e-16),label=label)
            ax.set(xlabel='Fo',ylabel=key);ax.grid(alpha=.3)
        # Actual saved times closest to requested times: never silently interpolate in time.
        chosen=sorted(set(int(np.argmin(abs(fos-fo))) for fo in PROFILE_FO))
        fp,ap=plt.subplots(figsize=(8,5))
        for j in chosen:
            fo,X,th,ref=prof[j]
            line,=ap.plot(X,ref,label=f'exact Fo={fo:.4g}')
            ap.plot(X,th,'o',ms=3,color=line.get_color())
            for xx,tt,rr in zip(X,th,ref):
                profile_rows.append(dict(label=label,Fo=fo,X=xx,theta_code=tt,theta_exact=rr))
        ap.set(xlabel='X',ylabel='theta',title=label+'; markers: KORSAR export')
        ap.grid(alpha=.3);ap.legend(fontsize=8,ncol=2)
        savefig(fp,out/f'comparison_profiles_{run_index:02d}.svg')
        ft,at=plt.subplots(figsize=(8,5))
        for xx in PROBES:
            at.semilogx(fos,[np.interp(xx,X,th) for _,X,th,_ in prof],label=f'export X={xx:g}')
            at.semilogx(fos,[exact([xx],fo,c['boundary'])[0][0] for fo in fos],'--',lw=.8)
        at.set(xlabel='Fo',ylabel='theta',title=label+'; dashed: exact')
        at.grid(alpha=.3);at.legend(fontsize=8);savefig(ft,out/f'comparison_histories_{run_index:02d}.svg')
        ff,af=plt.subplots(figsize=(8,5))
        for side in ('left','right'):
            line,=af.semilogx(fos,[r[f'q_{side}_W_m2'] for r in runrows],label=side+' export gradient')
            af.semilogx(fos,[r[f'q_{side}_ref_W_m2'] for r in runrows],'--',color=line.get_color(),label=side+' exact')
        af.set(xlabel='Fo',ylabel='q, W/m2',title=label);af.grid(alpha=.3);af.legend()
        savefig(ff,out/f'comparison_flux_{run_index:02d}.svg')
    for ax in axes: ax.legend(fontsize=6)
    savefig(fig,out/'errors_vs_fo.svg')
    write_csv(out/'metrics.csv',metrics);write_csv(out/'convergence_summary.csv',summary)
    write_csv(out/'comparison_profiles.csv',profile_rows)
    fig,axes=plt.subplots(1,2,figsize=(11,4.5))
    for dt in sorted(set(r['dt_max_s'] for r in summary)):
        group=sorted([r for r in summary if r['dt_max_s']==dt],key=lambda r:r['K'])
        if len(group)>1:
            for key,style in [('max_eT','o-'),('max_epsi_left','s--')]:
                axes[0].loglog([r['K']-1 for r in group],np.maximum([r[key] for r in group],1e-16),style,label=f'{key}, dt={dt:g}')
    for k in sorted(set(r['K'] for r in summary)):
        group=sorted([r for r in summary if r['K']==k],key=lambda r:r['dt_max_s'])
        if len(group)>1:
            for key,style in [('max_eT','o-'),('max_epsi_left','s--')]:
                axes[1].loglog([r['dt_max_s'] for r in group],np.maximum([r[key] for r in group],1e-16),style,label=f'{key}, K={k}')
    axes[0].set(xlabel='Intervals K-1',ylabel='Maximum error');axes[1].set(xlabel='dt_max, s',ylabel='Maximum error')
    for ax in axes:
        ax.grid(alpha=.3)
        if ax.lines: ax.legend(fontsize=6)
    savefig(fig,out/'convergence.svg')


def self_check():
    for boundary in ('dirichlet','insulated'):
        x=np.linspace(0,1,81)
        for fo in (.001,.01,.05,.1):
            a,b=fourier_solution(x,fo,boundary)
            c,d=image_solution(x,fo,boundary)
            np.testing.assert_allclose(a,c,atol=2e-12)
            np.testing.assert_allclose(b,d,atol=2e-12)
        th,ps=exact(x,10,boundary)
        np.testing.assert_allclose(th,1 if boundary=='insulated' else 1-x,atol=1e-9)
        np.testing.assert_allclose(ps,0 if boundary=='insulated' else 1,atol=1e-9)
        for fo in (.02,.2):
            h=1e-6
            derivative=(mean_theta(fo+h,boundary)-mean_theta(fo-h,boundary))/(2*h)
            flux=exact([0,1],fo,boundary)[1]
            np.testing.assert_allclose(derivative,flux[0]-flux[1],rtol=1e-7,atol=1e-8)
    assert np.isinf(exact([0],0)[1][0])
    np.testing.assert_allclose(exact([0],1e-6)[1][0],1/np.sqrt(np.pi*1e-6),rtol=1e-12)
    print('Self-check OK: series vs images, stationary limit, energy balance, early-time asymptotic.')


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--config',type=Path)
    p.add_argument('--boundary',choices=['dirichlet','insulated'])
    p.add_argument('--cases',type=Path,help='JSON list: label,csv,dt_max_s; paths relative to JSON')
    p.add_argument('--out',type=Path,default=Path('result/analysis'))
    p.add_argument('--fo-min',type=float,default=.01,help='Lower Fo for summary maxima, default .01')
    p.add_argument('--self-check',action='store_true')
    args=p.parse_args()
    if args.self_check:
        self_check()
        if args.config is None and args.cases is None: return
    c=DEFAULT.copy()
    if args.config:
        loaded=json.loads(args.config.read_text(encoding='utf-8-sig'))
        if set(loaded)-set(c): raise ValueError('Unknown configuration keys: '+str(set(loaded)-set(c)))
        c.update(loaded)
    if args.boundary: c['boundary']=args.boundary
    validate_config(c)
    if not np.isfinite(args.fo_min) or args.fo_min<=0: raise ValueError('fo-min must be positive')
    args.out.mkdir(parents=True,exist_ok=True)
    (args.out/'config_used.json').write_text(json.dumps(c,indent=2),encoding='utf-8')
    make_reference(c,args.out)
    if args.cases: process_runs(args.cases,c,args.out,args.fo_min)
    print(f'Output: {args.out.resolve()}')


if __name__=='__main__':
    main()
