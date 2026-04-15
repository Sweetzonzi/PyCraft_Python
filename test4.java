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
        if (getLevel().isClientSide()) return;

        Vector3f pos = agent.getPosition();
        Vector3f vel = new Vector3f();
        agent.getBody().getLinearVelocity(vel);
        Vector3f angularVelLocal = agent.getAngularVelocityLocal();
        Vector3f target = getTarget();

        // ========== 高度控制（第一步，保持不变）==========
        float ey = target.y - pos.y;

        integralY += ey * Dt;
        if (FastMath.abs(ey) < 0.1f) integralY *= 0.95f;
        integralY = clamp(integralY, -INTEGRAL_LIMIT_POS, INTEGRAL_LIMIT_POS);

        float vyDes = kpPosY * ey + kiPosY * integralY - kdPosY * vel.y;

        float totalThrust = mass * (gravity + vyDes);
        totalThrust = FastMath.clamp(totalThrust, 0.2f * mass * gravity, 4 * maxThrust * 0.8f);
        float baseThrust = totalThrust / 4.0f;

        // ========== 第二步新增：偏航控制（Yaw）==========
        float psiDes = getTargetYaw();
        float psi = agent.getYaw();

        // 偏航误差归一化到 -pi ~ pi
        float ePsi = psiDes - psi;
        while (ePsi > FastMath.PI) ePsi -= 2 * FastMath.PI;
        while (ePsi < -FastMath.PI) ePsi += 2 * FastMath.PI;

        // 偏航积分（可选，先不加看效果）
        // integralYaw += ePsi * Dt;
        // integralYaw = clamp(integralYaw, -INTEGRAL_LIMIT_ATT, INTEGRAL_LIMIT_ATT);

        // 期望偏航角速度（纯P控制，保守参数）
        float q = angularVelLocal.y;  // 当前偏航角速度
        float qDes = kpAttYaw * ePsi - kdAttYaw * q;  // PD控制，无积分

        // 限制角速度
        float maxRate = 2.0f;
        qDes = clamp(qDes, -maxRate, maxRate);

        // 偏航力矩
        float torqueGain = 0.1f;
        float torqueYaw = (qDes - q) * torqueGain;

        // 对角差速产生偏航（反扭矩）
        // 假设：LF+RB顺时针，RF+LB逆时针（或相反，根据实际调整符号）
        float yawDiff = torqueYaw / 4.0f;

        // ========== 电机分配（高度+偏航）==========
        // 左前(0): base - yawDiff
        // 右前(1): base + yawDiff
        // 左后(2): base + yawDiff
        // 右后(3): base - yawDiff
        float tLF = baseThrust - yawDiff;
        float tRF = baseThrust + yawDiff;
        float tLB = baseThrust + yawDiff;
        float tRB = baseThrust - yawDiff;

        // 限制推力范围
        tLF = clamp(tLF, 0.1f * maxThrust, 0.9f * maxThrust);
        tRF = clamp(tRF, 0.1f * maxThrust, 0.9f * maxThrust);
        tLB = clamp(tLB, 0.1f * maxThrust, 0.9f * maxThrust);
        tRB = clamp(tRB, 0.1f * maxThrust, 0.9f * maxThrust);

        thrusters.get(0).setTargetThrust(tLF / maxThrust);
        thrusters.get(1).setTargetThrust(tRF / maxThrust);
        thrusters.get(2).setTargetThrust(tLB / maxThrust);
        thrusters.get(3).setTargetThrust(tRB / maxThrust);

        // 调试
        if (agent.physicsTickCount % 20 == 0) {
            System.out.printf("[UAV-YAW] pos:%.2f,%.2f,%.2f errY:%.2f yawErr:%.2f thrust:%.2f%n",
                    pos.x, pos.y, pos.z, ey, ePsi * FastMath.RAD_TO_DEG, baseThrust / maxThrust);
        }
    }
}
