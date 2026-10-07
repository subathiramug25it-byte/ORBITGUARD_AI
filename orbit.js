/**
 * ORBITGUARD AI - Orbit Visualization Engine
 * High-performance HTML5 Canvas 2D orbital propagation and conjunction visualizer.
 * Renders Earth, LEO orbits, satellite with solar wings, multiple debris,
 * predicted intercept trajectories, and post-maneuver deflection paths.
 */

class OrbitVisualizer {
    constructor(canvasId) {
        this.canvas = document.getElementById(canvasId);
        if (!this.canvas) return;
        this.ctx = this.canvas.getContext('2d');

        this.width = this.canvas.width;
        this.height = this.canvas.height;
        this.centerX = this.width / 2;
        this.centerY = this.height / 2;
        this.scale = 0.024; // km to canvas pixels

        // State & Data
        this.isRunning = true;
        this.simTime = 0.0;
        this.timeScale = 0.02; // animation speed
        this.stars = this.generateStars(60);

        this.telemetry = null;
        this.trajectories = null;
        this.postTrajectories = null;
        this.conjunction = null;
        this.showPostTrajectory = true;

        this.setupDPI();
        this.animate = this.animate.bind(this);
        requestAnimationFrame(this.animate);
    }

    setupDPI() {
        const dpr = window.devicePixelRatio || 1;
        const rect = this.canvas.getBoundingClientRect();
        this.width = rect.width || 700;
        this.height = rect.height || 420;
        this.canvas.width = this.width * dpr;
        this.canvas.height = this.height * dpr;
        this.ctx.scale(dpr, dpr);
        this.centerX = this.width / 2;
        this.centerY = this.height / 2;
    }

    generateStars(count) {
        const stars = [];
        for (let i = 0; i < count; i++) {
            stars.push({
                x: Math.random() * 800,
                y: Math.random() * 500,
                radius: Math.random() * 1.2 + 0.4,
                alpha: Math.random() * 0.7 + 0.3,
                twinkleSpeed: Math.random() * 0.03 + 0.01
            });
        }
        return stars;
    }

    setData(telemetry, trajectories, postTrajectories, conjunction) {
        this.telemetry = telemetry;
        this.trajectories = trajectories;
        this.postTrajectories = postTrajectories;
        this.conjunction = conjunction;
    }

    toggleAnimation() {
        this.isRunning = !this.isRunning;
        return this.isRunning;
    }

    toggleTrajectoryMode() {
        this.showPostTrajectory = !this.showPostTrajectory;
        return this.showPostTrajectory;
    }

    resetView() {
        this.centerX = this.width / 2;
        this.centerY = this.height / 2;
    }

    animate(timestamp) {
        if (this.isRunning) {
            this.simTime += this.timeScale;
        }

        this.render();
        requestAnimationFrame(this.animate);
    }

    render() {
        const ctx = this.ctx;
        ctx.clearRect(0, 0, this.width, this.height);

        // 1. Draw Space Background & Twinkling Stars
        this.drawBackground(ctx);

        // 2. Draw Central Earth & Atmosphere
        this.drawEarth(ctx);

        // 3. Draw Orbit Rings (Baseline LEO)
        this.drawOrbitRings(ctx);

        // 4. Draw Trajectories (Pre & Post Maneuver)
        if (this.trajectories) {
            this.drawTrajectories(ctx);
        }

        // 5. Draw Debris Objects
        this.drawDebris(ctx);

        // 6. Draw Conjunction TCA Marker
        if (this.conjunction) {
            this.drawConjunctionMarker(ctx);
        }

        // 7. Draw Virtual Satellite
        this.drawSatellite(ctx);

        // 8. Draw Grid Overlay & Coordinate Crosshairs
        this.drawHUD(ctx);
    }

    drawBackground(ctx) {
        // Deep space gradient
        const bgGrad = ctx.createRadialGradient(
            this.centerX, this.centerY, 40,
            this.centerX, this.centerY, this.width / 1.4
        );
        bgGrad.addColorStop(0, '#0c1638');
        bgGrad.addColorStop(0.6, '#060a17');
        bgGrad.addColorStop(1, '#020408');
        ctx.fillStyle = bgGrad;
        ctx.fillRect(0, 0, this.width, this.height);

        // Twinkling stars
        for (let star of this.stars) {
            const currentAlpha = star.alpha + Math.sin(this.simTime * star.twinkleSpeed * 100) * 0.2;
            ctx.fillStyle = `rgba(255, 255, 255, ${Math.max(0.1, currentAlpha)})`;
            ctx.beginPath();
            ctx.arc(star.x, star.y, star.radius, 0, Math.PI * 2);
            ctx.fill();
        }
    }

    drawEarth(ctx) {
        const earthRadiusKm = 6371;
        const earthPixelRadius = earthRadiusKm * this.scale * 0.95; // ~145px scaled

        ctx.save();
        ctx.translate(this.centerX, this.centerY);

        // Atmospheric glow
        const glowGrad = ctx.createRadialGradient(0, 0, earthPixelRadius * 0.85, 0, 0, earthPixelRadius * 1.25);
        glowGrad.addColorStop(0, 'rgba(0, 180, 255, 0.4)');
        glowGrad.addColorStop(0.7, 'rgba(0, 110, 255, 0.15)');
        glowGrad.addColorStop(1, 'rgba(0, 40, 120, 0)');
        ctx.fillStyle = glowGrad;
        ctx.beginPath();
        ctx.arc(0, 0, earthPixelRadius * 1.25, 0, Math.PI * 2);
        ctx.fill();

        // Earth globe body
        const earthGrad = ctx.createRadialGradient(
            -earthPixelRadius * 0.35, -earthPixelRadius * 0.35, earthPixelRadius * 0.1,
            0, 0, earthPixelRadius
        );
        earthGrad.addColorStop(0, '#2d7df6');
        earthGrad.addColorStop(0.6, '#1847a6');
        earthGrad.addColorStop(0.85, '#0d2866');
        earthGrad.addColorStop(1, '#051133');

        ctx.fillStyle = earthGrad;
        ctx.beginPath();
        ctx.arc(0, 0, earthPixelRadius, 0, Math.PI * 2);
        ctx.fill();

        // Earth Continents / Cloud Swirls representation
        ctx.strokeStyle = 'rgba(78, 172, 109, 0.35)';
        ctx.lineWidth = 2.5;
        ctx.beginPath();
        ctx.arc(0, 0, earthPixelRadius * 0.65, 0.3 + this.simTime * 0.05, 1.8 + this.simTime * 0.05);
        ctx.stroke();

        ctx.beginPath();
        ctx.arc(0, 0, earthPixelRadius * 0.8, -1.2 + this.simTime * 0.05, 0.1 + this.simTime * 0.05);
        ctx.stroke();

        // Latitude grid lines
        ctx.strokeStyle = 'rgba(255, 255, 255, 0.08)';
        ctx.lineWidth = 1;
        ctx.beginPath();
        ctx.ellipse(0, 0, earthPixelRadius, earthPixelRadius * 0.35, 0, 0, Math.PI * 2);
        ctx.stroke();

        // Earth center label
        ctx.fillStyle = 'rgba(255, 255, 255, 0.7)';
        ctx.font = '10px JetBrains Mono';
        ctx.textAlign = 'center';
        ctx.fillText('EARTH (R=6371 km)', 0, 4);

        ctx.restore();
    }

    drawOrbitRings(ctx) {
        ctx.save();
        ctx.translate(this.centerX, this.centerY);

        const rSatKm = 6371 + (this.telemetry ? this.telemetry.satellite.altitude_km : 550);
        const satRadiusPx = rSatKm * this.scale * 0.95;

        // Satellite LEO orbit track
        ctx.strokeStyle = 'rgba(0, 229, 255, 0.2)';
        ctx.lineWidth = 1.2;
        ctx.setLineDash([4, 4]);
        ctx.beginPath();
        ctx.arc(0, 0, satRadiusPx, 0, Math.PI * 2);
        ctx.stroke();

        // Debris orbit track
        const rDebKm = 6371 + 550.35;
        const debRadiusPx = rDebKm * this.scale * 0.95;
        ctx.strokeStyle = 'rgba(255, 51, 75, 0.15)';
        ctx.lineWidth = 1;
        ctx.setLineDash([3, 5]);
        ctx.beginPath();
        ctx.ellipse(0, 0, debRadiusPx, debRadiusPx * 0.92, 0.4, 0, Math.PI * 2);
        ctx.stroke();

        ctx.restore();
    }

    drawTrajectories(ctx) {
        ctx.save();
        ctx.translate(this.centerX, this.centerY);

        const scale = this.scale * 0.95;

        // 1. Satellite Pre-Maneuver Path (Green/Cyan)
        if (this.trajectories.satellite && this.trajectories.satellite.length > 0) {
            ctx.strokeStyle = 'rgba(0, 230, 118, 0.6)';
            ctx.lineWidth = 1.8;
            ctx.setLineDash([3, 3]);
            ctx.beginPath();
            const satPath = this.trajectories.satellite;
            ctx.moveTo(satPath[0].x * scale, satPath[0].y * scale);
            for (let i = 1; i < satPath.length; i++) {
                ctx.lineTo(satPath[i].x * scale, satPath[i].y * scale);
            }
            ctx.stroke();
        }

        // 2. Primary Debris Predicted Path (Red)
        if (this.trajectories.debris) {
            const primaryKey = Object.keys(this.trajectories.debris)[0];
            const debPath = this.trajectories.debris[primaryKey];
            if (debPath && debPath.length > 0) {
                ctx.strokeStyle = 'rgba(255, 51, 75, 0.7)';
                ctx.lineWidth = 1.8;
                ctx.setLineDash([3, 3]);
                ctx.beginPath();
                ctx.moveTo(debPath[0].x * scale, debPath[0].y * scale);
                for (let i = 1; i < debPath.length; i++) {
                    ctx.lineTo(debPath[i].x * scale, debPath[i].y * scale);
                }
                ctx.stroke();
            }
        }

        // 3. Post-Maneuver Trajectory (Cyan Solid / Deflected)
        if (this.showPostTrajectory && this.postTrajectories && this.postTrajectories.satellite) {
            const postPath = this.postTrajectories.satellite;
            if (postPath.length > 0) {
                ctx.strokeStyle = '#00e5ff';
                ctx.lineWidth = 2.5;
                ctx.setLineDash([]); // solid line for active post-burn path
                ctx.shadowColor = '#00e5ff';
                ctx.shadowBlur = 10;
                ctx.beginPath();
                ctx.moveTo(postPath[0].x * scale, postPath[0].y * scale);
                for (let i = 1; i < postPath.length; i++) {
                    ctx.lineTo(postPath[i].x * scale, postPath[i].y * scale);
                }
                ctx.stroke();
                ctx.shadowBlur = 0; // reset
            }
        }

        ctx.restore();
    }

    drawSatellite(ctx) {
        ctx.save();
        ctx.translate(this.centerX, this.centerY);

        const rSatKm = 6371 + (this.telemetry ? this.telemetry.satellite.altitude_km : 550);
        const radiusPx = rSatKm * this.scale * 0.95;

        // Animate angular position
        let baseAngle = this.telemetry ? (this.telemetry.satellite.true_anomaly_deg * Math.PI / 180) : 0.8;
        let angle = baseAngle + this.simTime * 0.4;

        // If post maneuver applied, slightly offset radius
        if (this.postTrajectories) {
            // Deflected orbit visual shift
            angle += 0.08;
        }

        const satX = radiusPx * Math.cos(angle);
        const satY = radiusPx * Math.sin(angle);

        ctx.translate(satX, satY);
        ctx.rotate(angle + Math.PI / 2); // face along velocity vector

        // Glow
        ctx.shadowColor = '#00e676';
        ctx.shadowBlur = 12;

        // Satellite Body (Gold/Silver rectangle)
        ctx.fillStyle = '#ffecb3';
        ctx.fillRect(-5, -5, 10, 10);

        // Solar panels (Blue wings)
        ctx.fillStyle = '#00b0ff';
        ctx.fillRect(-15, -3, 8, 6);
        ctx.fillRect(7, -3, 8, 6);
        ctx.strokeStyle = '#fff';
        ctx.lineWidth = 0.5;
        ctx.strokeRect(-15, -3, 8, 6);
        ctx.strokeRect(7, -3, 8, 6);

        // Velocity vector arrow
        ctx.strokeStyle = '#00e676';
        ctx.lineWidth = 1.5;
        ctx.beginPath();
        ctx.moveTo(0, -6);
        ctx.lineTo(0, -18);
        ctx.stroke();
        ctx.beginPath();
        ctx.moveTo(-3, -14);
        ctx.lineTo(0, -18);
        ctx.lineTo(3, -14);
        ctx.stroke();

        ctx.shadowBlur = 0;

        // Label
        ctx.rotate(-(angle + Math.PI / 2)); // unrotate for label
        ctx.fillStyle = '#00e676';
        ctx.font = 'bold 10px JetBrains Mono';
        ctx.textAlign = 'left';
        ctx.fillText('🛰️ OG-SAT-1', 12, -8);

        ctx.restore();
    }

    drawDebris(ctx) {
        ctx.save();
        ctx.translate(this.centerX, this.centerY);

        const debrisList = this.telemetry ? this.telemetry.all_debris : [
            { id: "DEBRIS-ALPHA-92", name: "Cosmos-2251 #92", altitude_km: 550.35, true_anomaly_deg: 48.8, is_primary: true }
        ];

        for (let deb of debrisList) {
            const rKm = 6371 + deb.altitude_km;
            const radiusPx = rKm * this.scale * 0.95;
            let baseAngle = (deb.true_anomaly_deg * Math.PI / 180);
            let angle = baseAngle + this.simTime * 0.42; // slightly different speed

            const debX = radiusPx * Math.cos(angle);
            const debY = radiusPx * Math.sin(angle) * (deb.is_primary ? 0.95 : 0.88);

            ctx.save();
            ctx.translate(debX, debY);

            if (deb.is_primary) {
                // Primary Debris: Pulsing Hazard Circle
                const pulse = Math.sin(this.simTime * 5) * 4 + 8;
                ctx.strokeStyle = 'rgba(255, 51, 75, 0.4)';
                ctx.lineWidth = 1.5;
                ctx.beginPath();
                ctx.arc(0, 0, pulse, 0, Math.PI * 2);
                ctx.stroke();

                // Core marker
                ctx.fillStyle = '#ff334b';
                ctx.shadowColor = '#ff334b';
                ctx.shadowBlur = 10;
                ctx.beginPath();
                ctx.arc(0, 0, 4, 0, Math.PI * 2);
                ctx.fill();
                ctx.shadowBlur = 0;

                // Debris Label
                ctx.fillStyle = '#ff334b';
                ctx.font = 'bold 9px JetBrains Mono';
                ctx.textAlign = 'left';
                ctx.fillText(`☄️ ${deb.name || deb.id}`, 8, -6);
            } else {
                // Secondary Debris: small yellow/orange diamond
                ctx.fillStyle = '#ffd600';
                ctx.beginPath();
                ctx.arc(0, 0, 2.5, 0, Math.PI * 2);
                ctx.fill();

                ctx.fillStyle = 'rgba(255, 214, 0, 0.7)';
                ctx.font = '8px JetBrains Mono';
                ctx.textAlign = 'left';
                ctx.fillText(deb.name || deb.id, 6, -3);
            }

            ctx.restore();
        }

        ctx.restore();
    }

    drawConjunctionMarker(ctx) {
        ctx.save();
        ctx.translate(this.centerX, this.centerY);

        const scale = this.scale * 0.95;
        const caX = this.conjunction.x * scale;
        const caY = this.conjunction.y * scale;

        ctx.translate(caX, caY);

        // Pulsing warning crosshair
        const pulse = Math.sin(this.simTime * 6) * 3 + 10;
        ctx.strokeStyle = '#ffd600';
        ctx.lineWidth = 1.5;
        ctx.setLineDash([2, 2]);
        ctx.beginPath();
        ctx.arc(0, 0, pulse, 0, Math.PI * 2);
        ctx.stroke();

        ctx.setLineDash([]);
        // Crosshair ticks
        ctx.beginPath();
        ctx.moveTo(-pulse - 4, 0); ctx.lineTo(-pulse + 2, 0);
        ctx.moveTo(pulse - 2, 0);  ctx.lineTo(pulse + 4, 0);
        ctx.moveTo(0, -pulse - 4); ctx.lineTo(0, -pulse + 2);
        ctx.moveTo(0, pulse - 2);  ctx.lineTo(0, pulse + 4);
        ctx.stroke();

        // Label
        ctx.fillStyle = '#ffd600';
        ctx.font = 'bold 10px JetBrains Mono';
        ctx.textAlign = 'center';
        ctx.fillText(`⚠️ CONJUNCTION POINT`, 0, -pulse - 6);
        ctx.font = '9px JetBrains Mono';
        ctx.fillText(`Miss Dist: ${this.conjunction.min_distance_m}m | TCA: ${this.conjunction.tca_minutes}m`, 0, pulse + 12);

        ctx.restore();
    }

    drawHUD(ctx) {
        // Grid corner accents & scale legend
        ctx.save();
        ctx.strokeStyle = 'rgba(0, 229, 255, 0.15)';
        ctx.lineWidth = 1;

        // Top-left corner bracket
        ctx.beginPath();
        ctx.moveTo(15, 30); ctx.lineTo(15, 15); ctx.lineTo(30, 15);
        ctx.stroke();

        // Top-right corner bracket
        ctx.beginPath();
        ctx.moveTo(this.width - 30, 15); ctx.lineTo(this.width - 15, 15); ctx.lineTo(this.width - 15, 30);
        ctx.stroke();

        // Scale bar
        const barPx = 50;
        const barKm = Math.round(barPx / (this.scale * 0.95));
        ctx.strokeStyle = 'rgba(255, 255, 255, 0.4)';
        ctx.beginPath();
        ctx.moveTo(this.width - 70, this.height - 25);
        ctx.lineTo(this.width - 20, this.height - 25);
        ctx.stroke();

        ctx.fillStyle = 'rgba(255, 255, 255, 0.6)';
        ctx.font = '8px JetBrains Mono';
        ctx.textAlign = 'center';
        ctx.fillText(`~${barKm} km`, this.width - 45, this.height - 12);

        ctx.restore();
    }
}

// Global instance
let orbitVisualizer = null;

function initOrbitCanvas() {
    orbitVisualizer = new OrbitVisualizer('orbitCanvas');
}

function updateOrbitData(telemetry, trajectories, postTrajectories, conjunction) {
    if (orbitVisualizer) {
        orbitVisualizer.setData(telemetry, trajectories, postTrajectories, conjunction);
    }
}

function toggleOrbitAnimation() {
    if (orbitVisualizer) {
        const isRunning = orbitVisualizer.toggleAnimation();
        const icon = document.getElementById('animPlayIcon');
        if (icon) {
            icon.innerText = isRunning ? "⏸️ PAUSE" : "▶️ RESUME";
        }
    }
}

function toggleTrajectoryMode() {
    if (orbitVisualizer) {
        const show = orbitVisualizer.toggleTrajectoryMode();
        const txt = document.getElementById('trajToggleText');
        if (txt) {
            txt.innerText = show ? "PRE & POST" : "PRE ONLY";
        }
    }
}

function resetCanvasView() {
    if (orbitVisualizer) {
        orbitVisualizer.resetView();
    }
}
