package io.github.sweetzonzi.py_port.common.agent.component;


import com.jme3.math.FastMath;
import com.jme3.math.Quaternion;
import com.jme3.math.Vector3f;
import io.github.sweetzonzi.py_port.common.agent.AbstractAgent;
import net.minecraft.network.syncher.EntityDataAccessor;
import net.minecraft.network.syncher.EntityDataSerializers;
import net.minecraft.network.syncher.SynchedEntityData;
import net.minecraft.world.phys.Vec3;

import java.util.List;

import static com.jme3.math.FastMath.clamp;

public class QuatUavCtrlComponent extends AbstractAgentComponent {
    private final List<ThrusterComponent> thrusters;

    // 同步数据定义
    protected static final EntityDataAccessor<Float> TARGET_X = SynchedEntityData.defineId(QuatUavCtrlComponent.class, EntityDataSerializers.FLOAT);
    protected static final EntityDataAccessor<Float> TARGET_Y = SynchedEntityData.defineId(QuatUavCtrlComponent.class, EntityDataSerializers.FLOAT);
    protected static final EntityDataAccessor<Float> TARGET_Z = SynchedEntityData.defineId(QuatUavCtrlComponent.class, EntityDataSerializers.FLOAT);
    protected static final EntityDataAccessor<Float> TARGET_YAW = SynchedEntityData.defineId(QuatUavCtrlComponent.class, EntityDataSerializers.FLOAT);

    // 物理参数
    private float mass;
    private final  float gravity = 9.81f;
    private float armLength;
    private float maxThrust;

    // 外环PID参数
    private float kpPosX = 0.5f;
    private float kpPosY = 0.5f;
    private float kpPosZ = 1.5f;

    private float kiPosX = 0.05f;
    private float kiPosY = 0.05f;
    private float kiPosZ = 0.1f;

    private float kdPosX = 1.0f;
    private float kdPosY = 1.0f;
    private float kdPosZ = 2.0f;

    // 内环PID参数
    private float kpAttRoll = 5.0f;
    private float kpAttPitch = 5.0f;
    private float kpAttYaw = 2.0f;

    private float kiAttRoll = 0.1f;
    private float kiAttPitch = 0.1f;
    private float kiAttYaw = 0.1f;

    private float kdAttRoll = 0.5f;
    private float kdAttPitch = 0.5f;
    private float kdAttYaw = 0.5f;

    //积分项
    private float integralX = 0, integralY = 0, integralZ = 0;
    private float integralRoll = 0, integralPitch = 0, integralYaw = 0;

    private static  final float INTEGRAL_LIMIT_POS = 1.0f;
    private static final float INTEGRAL_LIMIT_ATT = 1.0f;
    private static  final float Dt = 0.02f;

    public QuatUavCtrlComponent(String name, AbstractAgent agent, List<ThrusterComponent> thrusters) {
        super(name, agent);
        this.thrusters = thrusters;
        this.mass = agent.getBody().getMass();
        this.armLength = thrusters.get(0).getOffset().length();
        this.maxThrust = thrusters.get(0).getMaxThrust();
    }

    // 定义同步数据
    @Override
    protected void defineSyncedData(SynchedEntityData.Builder builder) {
        builder.define(TARGET_X, 0f);
        builder.define(TARGET_Y, 0f);
        builder.define(TARGET_Z, 0f);
        builder.define(TARGET_YAW, 0f);
    }
    // 设置目标位置
    public void setTarget(Vector3f pos) {
        this.syncedData.set(TARGET_X, pos.x);
        this.syncedData.set(TARGET_Y, pos.y);
        this.syncedData.set(TARGET_Z, pos.z);
    }

    public void setTarget(Vec3 pos) {
        setTarget(new Vector3f((float) pos.x, (float) pos.y, (float) pos.z));
    }

    // 获取目标位置
    public Vector3f getTarget() {
        return new Vector3f(
                this.syncedData.get(TARGET_X),
                this.syncedData.get(TARGET_Y),
                this.syncedData.get(TARGET_Z)
        );
    }

    // 设置、获取目标Yaw
    public void setTargetYaw(float yawDegrees) {
        this.syncedData.set(TARGET_YAW, yawDegrees * FastMath.DEG_TO_RAD);
    }

    public float getTargetYaw() {
        return this.syncedData.get(TARGET_YAW);
    }

    // 悬停在当前位置
    public void hover() {
        setTarget(agent.getPosition());
        setTargetYaw(agent.getYaw() * FastMath.RAD_TO_DEG);  // 保持当前偏航角
        resetIntegrals();
    }

    //
    public void resetIntegrals(){
        integralX = integralY = integralZ = 0;
        integralRoll = integralPitch = integralYaw = 0;
    }


    @Override
    public void prePhysicsTick() {
        super.prePhysicsTick();

        // 只在服务端计算
        if (getLevel().isClientSide()) return;

        // 获取当前状态
        Vector3f pos = agent.getPosition();
        Vector3f vel = new Vector3f();
        agent.getBody().getLinearVelocity(vel);
        Vector3f angularVelLocal = agent.getAngularVelocityLocal();  // 机体坐标系角速度

        // 获取目标
        Vector3f target = getTarget();

        // 外环控制
        float ex = target.x - pos.x;
        float ey = target.y - pos.y;
        float ez = target.z - pos.z;

        //积分
        integralX += ex * Dt;
        integralY += ey * Dt;
        integralZ += ez * Dt;
        if (FastMath.abs(ex) < 0.1f) integralX *= 0.95f;
        if (FastMath.abs(ey) < 0.1f) integralY *= 0.95f;
        if (FastMath.abs(ez) < 0.1f) integralZ *= 0.95f;

        integralX = clamp(integralX, -INTEGRAL_LIMIT_POS, INTEGRAL_LIMIT_POS);
        integralY = clamp(integralY, -INTEGRAL_LIMIT_POS, INTEGRAL_LIMIT_POS);
        integralZ = clamp(integralZ, -INTEGRAL_LIMIT_POS, INTEGRAL_LIMIT_POS);

        // 计算期望速度
        float vxDes = kpPosX * ex + kiPosX * integralX - kdPosX * vel.x;
        float vyDes = kpPosY * ey + kiPosY * integralY - kdPosY * vel.y;
        float vzDes = kpPosZ * ez + kiPosZ * integralZ - kdPosZ * vel.z;

        // 总推力（高度控制）
        float totalThrust = mass * (gravity + vyDes);
        totalThrust = FastMath.clamp(totalThrust, 0, 4 * maxThrust * 0.9f);
        float baseThrust = totalThrust / 4.0f;

        // 期望速度到期望姿态角
        float vHoriz = FastMath.sqrt(vxDes * vxDes + vzDes * vzDes);

        // 滚转（控制x移动）:控制z方向移动，俯仰（控制z移动）：控制x方向移动
        float phiDes = FastMath.atan2(vzDes * mass, totalThrust);
        float thetaDes = FastMath.atan2(-vxDes * mass, totalThrust);

        // 限制倾斜角
        float maxTilt = 20 * FastMath.DEG_TO_RAD;  // 保守20度
        phiDes = clamp(phiDes, -maxTilt, maxTilt);
        thetaDes = clamp(thetaDes, -maxTilt, maxTilt);

        float psiDes = getTargetYaw(); // 期望偏航角

        // 获取当前姿态
        float phi = agent.getRoll(); //roll
        float theta = agent.getPitch(); // pitch
        float psi = agent.getYaw(); // yaw

        float p = angularVelLocal.x;     // 绕X角速度（滚转速率）
        float q = angularVelLocal.y;     // 绕Y角速度（偏航速率）
        float r = angularVelLocal.z;     // 绕Z角速度（俯仰速率）

        // 内环姿态控制
        float ePhi = phiDes - phi;           // Roll误差
        float eTheta = thetaDes - theta;     // Pitch误差
        float ePsi = psiDes - psi;           // Yaw误差

        // Yaw误差归一化到 -pi ~ pi
        while (ePsi > FastMath.PI) ePsi -= 2 * FastMath.PI;
        while (ePsi < -FastMath.PI) ePsi += 2 * FastMath.PI;

        // 姿态积分
        integralRoll += ePhi * Dt;
        integralPitch += eTheta * Dt;
        integralYaw += ePsi * Dt;
        integralRoll = FastMath.clamp(integralRoll, -INTEGRAL_LIMIT_ATT, INTEGRAL_LIMIT_ATT);
        integralPitch = FastMath.clamp(integralPitch, -INTEGRAL_LIMIT_ATT, INTEGRAL_LIMIT_ATT);
        integralYaw = FastMath.clamp(integralYaw, -INTEGRAL_LIMIT_ATT, INTEGRAL_LIMIT_ATT);

        // 期望角速度
        //float pDes = kpAttRoll * ePhi + kiAttRoll * integralRoll - kdAttRoll * p;
        //float qDes = kpAttYaw * ePsi + kiAttYaw * integralYaw - kdAttYaw * q;
        //float rDes = kpAttPitch * eTheta + kiAttPitch * integralPitch - kdAttPitch * r;

        float pDes = kpAttRoll * ePhi - kdAttRoll * p;
        float qDes = kpAttYaw * ePsi - kdAttYaw * q;
        float rDes = kpAttPitch * eTheta - kdAttPitch * r;

        // 角速度到力矩
        // 直接用力矩系数
        float torqueRoll = (pDes - p) * 0.05f;    // 绕X轴力矩（控制Roll）
        float torqueYaw = (qDes - q) * 0.1f;     // 绕Y轴力矩（控制Yaw）
        float torquePitch = (rDes - r) * 0.1f;   // 绕Z轴力矩（控制Pitch）



        // 电机分配（X型布局）
        float rollDiff = torqueRoll / (2 * armLength);   // 左右差速
        float pitchDiff = torquePitch / (2 * armLength); // 前后差速
        float yawDiff = torqueYaw / 4.0f;                // 对角差速

        // 左前(0): -roll, -pitch
        float tLF = baseThrust - rollDiff - pitchDiff - yawDiff;
        // 右前(1): +roll, -pitch
        float tRF = baseThrust + rollDiff - pitchDiff + yawDiff;
        // 左后(2): -roll, +pitch
        float tLB = baseThrust - rollDiff + pitchDiff + yawDiff;
        // 右后(3): +roll, +pitch
        float tRB = baseThrust + rollDiff + pitchDiff - yawDiff;

        // 应用
        thrusters.get(0).setTargetThrust(FastMath.clamp(tLF / maxThrust, 0f, 1f));
        thrusters.get(1).setTargetThrust(FastMath.clamp(tRF / maxThrust, 0f, 1f));
        thrusters.get(2).setTargetThrust(FastMath.clamp(tLB / maxThrust, 0f, 1f));
        thrusters.get(3).setTargetThrust(FastMath.clamp(tRB / maxThrust, 0f, 1f));

        // 调试
        if (agent.physicsTickCount % 20 == 0) {
            System.out.printf("[UAV] pos:%.2f,%.2f,%.2f err:%.2f,%.2f,%.2f roll:%.2f pitch:%.2f thrust:%.2f%n",
                    pos.x, pos.y, pos.z, ex, ey, ez, phi * FastMath.RAD_TO_DEG, theta * FastMath.RAD_TO_DEG, baseThrust / maxThrust);


        }
    }
}
