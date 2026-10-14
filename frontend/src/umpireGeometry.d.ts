export type PitchLocation = {
    x: number;
    y: number;
};
export declare const ZONE: {
    readonly left: 0.18;
    readonly right: 0.82;
    readonly top: 0.28;
    readonly bottom: 0.74;
    readonly ballRadius: 0.05;
};
export declare function isStrike(pitch: PitchLocation): boolean;
export declare function platePoint(pitch: PitchLocation): {
    x: number;
    y: number;
};
