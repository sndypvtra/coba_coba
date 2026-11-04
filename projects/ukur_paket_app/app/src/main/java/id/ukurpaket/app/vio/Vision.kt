package id.ukurpaket.app.vio

import kotlin.math.hypot
import kotlin.math.max
import kotlin.math.sqrt

/** Pinhole camera on the upright tracking picture. */
class Intrinsics(val f: Double, val cx: Double, val cy: Double)

/** A point's observations for the solver: frame indices and pixel positions (upright tracking picture). */
class PointObs(val id: Int, val k: IntArray, val u: DoubleArray, val v: DoubleArray)

/** Camera k: world <- camera rotation [r] (3x3) and centre [c] (world). */
class Cam(var r: DoubleArray, var c: DoubleArray)

class Structure(val cams: Array<Cam>, val points: Map<Int, DoubleArray>, val err: Map<Int, Double>) {
    val medianErr get() = err.values.sorted().let { if (it.isEmpty()) 99.0 else it[it.size / 2] }
}

object Vision {
    /** Observations used per point by the solver (evenly spaced along the track). */
    const val MAX_OBS = 14

    fun cap(p: PointObs, m: Int = MAX_OBS): PointObs {
        if (p.k.size <= m) return p
        val idx = IntArray(m) { (it * (p.k.size - 1).toDouble() / (m - 1)).toInt() }
        return PointObs(p.id, IntArray(m) { p.k[idx[it]] }, DoubleArray(m) { p.u[idx[it]] }, DoubleArray(m) { p.v[idx[it]] })
    }

    /**
     * Linear stage. With the rotations [rwc] (world <- camera, per frame) known, every observation says the point lies
     * on its viewing ray: (R[0] - x R[2]).(X - c) = 0 and (R[1] - y R[2]).(X - c) = 0 (R = camera <- world). These rows
     * are homogeneous (shrinking everything to nothing fits them too), so the scale is fixed to |c| = 1 and the answer
     * is the smallest eigenvector of the reduced camera system, points eliminated by the Schur complement.
     * Rows are reweighted to pixel errors (divided by depth, Huber at 2 px) over [iters] rounds.
     */
    fun linear(rwc: Array<DoubleArray>, pts: List<PointObs>, cam: Intrinsics, iters: Int = 3): Structure {
        val k = rwc.size; val nc = 3 * (k - 1)
        val rcw = Array(k) { M3.t(rwc[it]) }
        val use = pts.filter { it.k.size >= 3 }.map { cap(it) }
        val wt = use.map { DoubleArray(it.k.size) { 1.0 } }
        val dep = use.map { DoubleArray(it.k.size) { 1.0 } }
        var cs = Array(k) { DoubleArray(3) }
        var xs = HashMap<Int, DoubleArray>(); val errs = HashMap<Int, Double>()
        repeat(iters) {
            val s = DoubleArray(nc * nc)
            val keep = ArrayList<Triple<Int, Array<DoubleArray>, DoubleArray>>()   // point index, M per obs, Hpp^-1
            for ((pi, p) in use.withIndex()) {
                val ms = Array(p.k.size) { DoubleArray(9) }
                val hpp = DoubleArray(9)
                for (j in p.k.indices) {
                    val r = rcw[p.k[j]]; val x = (p.u[j] - cam.cx) / cam.f; val y = (p.v[j] - cam.cy) / cam.f
                    val a1 = doubleArrayOf(r[0] - x * r[6], r[1] - x * r[7], r[2] - x * r[8])
                    val a2 = doubleArrayOf(r[3] - y * r[6], r[4] - y * r[7], r[5] - y * r[8])
                    val w = wt[pi][j] / dep[pi][j]; val w2 = w * w
                    for (a in 0 until 3) for (b in 0 until 3) { val v = w2 * (a1[a] * a1[b] + a2[a] * a2[b]); ms[j][3 * a + b] = v; hpp[3 * a + b] += v }
                }
                val ev = M3.symEig(hpp)
                if (ev[0] < 1e-5 * ev[2]) continue
                val hi = M3.inv(hpp) ?: continue
                keep.add(Triple(pi, ms, hi))
                for (j in p.k.indices) {
                    val kj = p.k[j]; if (kj == 0) continue
                    val o = 3 * (kj - 1)
                    for (a in 0 until 3) for (b in 0 until 3) s[(o + a) * nc + o + b] += ms[j][3 * a + b]
                    val mh = M3.mul(ms[j], hi)
                    for (l in p.k.indices) {
                        val kl = p.k[l]; if (kl == 0) continue
                        val ol = 3 * (kl - 1)
                        val blk = M3.mul(mh, ms[l])
                        for (a in 0 until 3) for (b in 0 until 3) s[(o + a) * nc + ol + b] -= blk[3 * a + b]
                    }
                }
            }
            // a frame that sees (almost) nothing (blank, blurred) would leave its centre free and the system singular:
            // it is tied to the middle of its neighbours (homogeneous, so the scale stays free)
            val seen = IntArray(k); for ((pi, _, _) in keep) for (kk in use[pi].k) seen[kk]++
            var md = 0.0; var nd = 0
            for (i in 0 until nc) if (s[i * nc + i] > 0) { md += s[i * nc + i]; nd++ }
            val tw = if (nd > 0) md / nd else 1.0
            for (f in 1 until k) if (seen[f] < 6) {
                val nb = listOf(f - 1, f + 1).filter { it in 0 until k }
                val coef = HashMap<Int, Double>(); coef[f] = 1.0; for (q in nb) coef[q] = (coef[q] ?: 0.0) - 1.0 / nb.size
                for ((ka, va) in coef) for ((kb, vb) in coef) {
                    if (ka == 0 || kb == 0) continue
                    for (a in 0 until 3) s[(3 * (ka - 1) + a) * nc + 3 * (kb - 1) + a] += tw * va * vb
                }
            }
            val x = Dense.smallestEigvec(s, nc)
            cs = Array(k) { if (it == 0) DoubleArray(3) else doubleArrayOf(x[3 * (it - 1)], x[3 * (it - 1) + 1], x[3 * (it - 1) + 2]) }
            xs = HashMap()
            for ((pi, ms, hi) in keep) {
                val p = use[pi]; val acc = DoubleArray(3)
                for (j in p.k.indices) { val mc = M3.mv(ms[j], cs[p.k[j]]); for (a in 0 until 3) acc[a] += mc[a] }
                xs[p.id] = M3.mv(hi, acc)
            }
            // the eigenvector's sign is free: points must lie in front of the cameras
            var front = 0; var back = 0
            for ((pi, _, _) in keep.take(300)) { val p = use[pi]; val z = depth(rcw[p.k[0]], xs[p.id]!!, cs[p.k[0]]); if (z > 0) front++ else back++ }
            if (back > front) { cs = Array(k) { i -> DoubleArray(3) { -cs[i][it] } }; for (e in xs.entries) e.setValue(DoubleArray(3) { -e.value[it] }) }
            errs.clear()
            // a depth floor at 20 % of the median: a near-zero depth would give one bad point an enormous weight
            val zs = ArrayList<Double>()
            for ((pi, _, _) in keep.take(400)) { val p = use[pi]; val z = depth(rcw[p.k[0]], xs[p.id]!!, cs[p.k[0]]); if (z > 0) zs.add(z) }
            val zFloor = if (zs.isEmpty()) 1e-4 else 0.2 * zs.sorted()[zs.size / 2]
            for ((pi, _, _) in keep) {
                val p = use[pi]; val X = xs[p.id]!!
                val e = DoubleArray(p.k.size)
                for (j in p.k.indices) {
                    val xc = M3.mv(rcw[p.k[j]], doubleArrayOf(X[0] - cs[p.k[j]][0], X[1] - cs[p.k[j]][1], X[2] - cs[p.k[j]][2]))
                    dep[pi][j] = max(xc[2], zFloor)
                    e[j] = if (xc[2] > 0) cam.f * hypot(xc[0] / xc[2] - (p.u[j] - cam.cx) / cam.f, xc[1] / xc[2] - (p.v[j] - cam.cy) / cam.f) else 99.0
                    wt[pi][j] = if (xc[2] <= 0) 0.0 else if (e[j] < 2.0) 1.0 else 2.0 / e[j]
                }
                errs[p.id] = e.sorted()[e.size / 2]
            }
        }
        return Structure(Array(k) { Cam(rwc[it], cs[it]) }, xs, HashMap(errs))
    }

    private fun depth(rcw: DoubleArray, x: DoubleArray, c: DoubleArray) = rcw[6] * (x[0] - c[0]) + rcw[7] * (x[1] - c[1]) + rcw[8] * (x[2] - c[2])

    /**
     * Bundle adjustment: rotations, centres and points refined together on the reprojection error (Huber 1,5 px),
     * Gauss-Newton / Levenberg-Marquardt with the points eliminated (Schur). The sensor rotations are a prior
     * ([sigRotDeg]); the first centre is fixed and the others are held loosely to the linear answer, so the scale stays
     * for the inertial stage to set. Returns the refined structure; err = worst pixel error per point, 99 below 3 deg
     * parallax (an unreliable depth).
     */
    fun bundleAdjust(s0: Structure, pts: List<PointObs>, cam: Intrinsics, sigRotDeg: Double = 0.5, iters: Int = 6): Structure {
        val k = s0.cams.size
        val use = pts.filter { s0.points.containsKey(it.id) && (s0.err[it.id] ?: 99.0) < 4.0 }.map { cap(it, 16) }
        val r0 = Array(k) { s0.cams[it].r.copyOf() }
        val rot = Array(k) { s0.cams[it].r.copyOf() }
        val cen = Array(k) { s0.cams[it].c.copyOf() }
        val c0 = Array(k) { s0.cams[it].c.copyOf() }
        val X = HashMap<Int, DoubleArray>(); for (p in use) X[p.id] = s0.points[p.id]!!.copyOf()
        var scaleRef = 0.0; for (c in cen) scaleRef = max(scaleRef, sqrt(c[0] * c[0] + c[1] * c[1] + c[2] * c[2]))
        val sigC = 0.2 * max(scaleRef, 1e-6)
        val sigR = Math.toRadians(sigRotDeg)
        val nc = 6 * k
        var lambda = 1e-3
        fun cost(): Double {
            var c = 0.0
            for (p in use) { val x = X[p.id]!!; for (j in p.k.indices) c += huber(reproj(rot[p.k[j]], cen[p.k[j]], x, p.u[j], p.v[j], cam), 1.5) }
            for (i in 0 until k) { val th = M3.log(M3.mul(M3.t(r0[i]), rot[i])); c += (th[0] * th[0] + th[1] * th[1] + th[2] * th[2]) / (sigR * sigR) }
            for (i in 1 until k) for (a in 0 until 3) { val d = (cen[i][a] - c0[i][a]) / sigC; c += d * d }
            return c
        }
        var cur = cost()
        for (it in 0 until iters) {
            val hcc = DoubleArray(nc * nc); val gc = DoubleArray(nc)
            val blocks = ArrayList<PointBlock>()
            for (p in use) {
                val x = X[p.id]!!
                val hpp = DoubleArray(9); val gp = DoubleArray(3)
                val jcs = ArrayList<Pair<Int, DoubleArray>>()          // frame, Jc^T W Jp (6x3)
                val camTerms = ArrayList<CamTerm>()
                for (j in p.k.indices) {
                    val kk = p.k[j]; val rcw = M3.t(rot[kk]); val d = doubleArrayOf(x[0] - cen[kk][0], x[1] - cen[kk][1], x[2] - cen[kk][2])
                    val xc = M3.mv(rcw, d); val z = xc[2]
                    if (z < 1e-3) continue
                    val ru = cam.f * xc[0] / z + cam.cx - p.u[j]; val rv = cam.f * xc[1] / z + cam.cy - p.v[j]
                    val e = hypot(ru, rv); val w = if (e <= 1.5) 1.0 else 1.5 / e
                    // d(pixel)/d(Xc)
                    val pu = doubleArrayOf(cam.f / z, 0.0, -cam.f * xc[0] / (z * z)); val pv = doubleArrayOf(0.0, cam.f / z, -cam.f * xc[1] / (z * z))
                    // Xc wrt rotation increment: [Xc]x ; wrt centre: -Rcw ; wrt point: Rcw
                    val sk = doubleArrayOf(0.0, -xc[2], xc[1], xc[2], 0.0, -xc[0], -xc[1], xc[0], 0.0)
                    val ju = DoubleArray(6); val jv = DoubleArray(6); val jpu = DoubleArray(3); val jpv = DoubleArray(3)
                    for (b in 0 until 3) {
                        ju[b] = pu[0] * sk[b] + pu[1] * sk[3 + b] + pu[2] * sk[6 + b]
                        jv[b] = pv[0] * sk[b] + pv[1] * sk[3 + b] + pv[2] * sk[6 + b]
                        jpu[b] = pu[0] * rcw[b] + pu[1] * rcw[3 + b] + pu[2] * rcw[6 + b]
                        jpv[b] = pv[0] * rcw[b] + pv[1] * rcw[3 + b] + pv[2] * rcw[6 + b]
                        ju[3 + b] = -jpu[b]; jv[3 + b] = -jpv[b]
                    }
                    for (a in 0 until 3) { gp[a] += w * (jpu[a] * ru + jpv[a] * rv); for (b in 0 until 3) hpp[3 * a + b] += w * (jpu[a] * jpu[b] + jpv[a] * jpv[b]) }
                    val hcp = DoubleArray(18)
                    for (a in 0 until 6) for (b in 0 until 3) hcp[3 * a + b] = w * (ju[a] * jpu[b] + jv[a] * jpv[b])
                    jcs.add(kk to hcp)
                    camTerms.add(CamTerm(kk, ju, jv, ru, rv, w))
                }
                if (jcs.size < 2) { camTerms.clear(); continue }
                // the point's camera terms count only now that the point is kept
                for (t in camTerms) {
                    val o = 6 * t.k
                    for (a in 0 until 6) {
                        gc[o + a] += t.w * (t.ju[a] * t.ru + t.jv[a] * t.rv)
                        for (b in 0 until 6) hcc[(o + a) * nc + o + b] += t.w * (t.ju[a] * t.ju[b] + t.jv[a] * t.jv[b])
                    }
                }
                camTerms.clear()
                for (a in 0 until 3) hpp[4 * a] *= 1 + lambda
                val hi = M3.inv(hpp) ?: continue
                blocks.add(PointBlock(p.id, jcs, hi, gp))
                // Schur: Hcc -= Hcp Hpp^-1 Hpc ; gc -= Hcp Hpp^-1 gp
                for ((ka, ha) in jcs) {
                    val oa = 6 * ka
                    val hahi = DoubleArray(18)
                    for (a in 0 until 6) for (b in 0 until 3) hahi[3 * a + b] = ha[3 * a] * hi[b] + ha[3 * a + 1] * hi[3 + b] + ha[3 * a + 2] * hi[6 + b]
                    for (a in 0 until 6) gc[oa + a] -= hahi[3 * a] * gp[0] + hahi[3 * a + 1] * gp[1] + hahi[3 * a + 2] * gp[2]
                    for ((kb, hb) in jcs) {
                        val ob = 6 * kb
                        for (a in 0 until 6) for (b in 0 until 6)
                            hcc[(oa + a) * nc + ob + b] -= hahi[3 * a] * hb[3 * b] + hahi[3 * a + 1] * hb[3 * b + 1] + hahi[3 * a + 2] * hb[3 * b + 2]
                    }
                }
            }
            // priors: rotations to the sensors, centres loosely to the linear answer, the first centre fixed
            for (i in 0 until k) {
                val th = M3.log(M3.mul(M3.t(r0[i]), rot[i]))
                for (a in 0 until 3) { hcc[(6 * i + a) * nc + 6 * i + a] += 1 / (sigR * sigR); gc[6 * i + a] += th[a] / (sigR * sigR) }
                val wc = if (i == 0) 1e8 else 1 / (sigC * sigC)
                for (a in 0 until 3) { hcc[(6 * i + 3 + a) * nc + 6 * i + 3 + a] += wc; gc[6 * i + 3 + a] += wc * (cen[i][a] - c0[i][a]) }
            }
            for (i in 0 until nc) hcc[i * nc + i] *= 1 + lambda
            val dc = Dense.solve(hcc, DoubleArray(nc) { -gc[it] }, nc)
            // apply, with the point updates from back substitution
            val rotB = Array(k) { rot[it].copyOf() }; val cenB = Array(k) { cen[it].copyOf() }
            val xB = HashMap<Int, DoubleArray>(); for ((id, v) in X) xB[id] = v.copyOf()
            for (i in 0 until k) {
                rot[i] = M3.mul(rot[i], M3.exp(dc[6 * i], dc[6 * i + 1], dc[6 * i + 2]))
                for (a in 0 until 3) cen[i][a] += dc[6 * i + 3 + a]
            }
            for (b in blocks) {
                val rhs = DoubleArray(3) { -b.gp[it] }
                for ((kk, h) in b.jcs) for (a in 0 until 3) { var s = 0.0; for (c in 0 until 6) s += h[3 * c + a] * dc[6 * kk + c]; rhs[a] -= s }
                val dx = M3.mv(b.hi, rhs); val x = X[b.id]!!
                for (a in 0 until 3) x[a] += dx[a]
            }
            val nxt = cost()
            if (nxt < cur) { cur = nxt; lambda = max(lambda / 3, 1e-7) }
            else {
                for (i in 0 until k) { rot[i] = rotB[i]; cen[i] = cenB[i] }
                for ((id, v) in xB) X[id] = v
                lambda *= 10
            }
        }
        // per point: worst pixel error, and parallax between its first and last view
        val err = HashMap<Int, Double>()
        for (p in use) {
            val x = X[p.id]!!
            var worst = 0.0
            for (j in p.k.indices) worst = max(worst, reproj(rot[p.k[j]], cen[p.k[j]], x, p.u[j], p.v[j], cam))
            val a = DoubleArray(3) { cen[p.k.first()][it] - x[it] }; val b = DoubleArray(3) { cen[p.k.last()][it] - x[it] }
            val cosv = (a[0] * b[0] + a[1] * b[1] + a[2] * b[2]) / (sqrt(a[0] * a[0] + a[1] * a[1] + a[2] * a[2]) * sqrt(b[0] * b[0] + b[1] * b[1] + b[2] * b[2]) + 1e-12)
            val par = Math.toDegrees(kotlin.math.acos(cosv.coerceIn(-1.0, 1.0)))
            err[p.id] = if (par >= 3.0) worst else 99.0
        }
        return Structure(Array(k) { Cam(rot[it], cen[it]) }, X, err)
    }

    private class CamTerm(val k: Int, val ju: DoubleArray, val jv: DoubleArray, val ru: Double, val rv: Double, val w: Double)

    private class PointBlock(val id: Int, val jcs: List<Pair<Int, DoubleArray>>, val hi: DoubleArray, val gp: DoubleArray)

    fun reproj(rwc: DoubleArray, c: DoubleArray, x: DoubleArray, u: Double, v: Double, cam: Intrinsics): Double {
        val d0 = x[0] - c[0]; val d1 = x[1] - c[1]; val d2 = x[2] - c[2]
        val xc = rwc[0] * d0 + rwc[3] * d1 + rwc[6] * d2; val yc = rwc[1] * d0 + rwc[4] * d1 + rwc[7] * d2; val zc = rwc[2] * d0 + rwc[5] * d1 + rwc[8] * d2
        if (zc <= 1e-6) return 99.0
        return hypot(cam.f * xc / zc + cam.cx - u, cam.f * yc / zc + cam.cy - v)
    }

    private fun huber(e: Double, d: Double) = if (e <= d) e * e else 2 * d * e - d * d
}
