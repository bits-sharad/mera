interface Result {
    success: boolean;
    actual: number;
    expected: number;
}

interface ActualDimensionsResult {
    x?: Result;
    y?: Result;
    width?: Result;
    height?: Result;
}

export default ActualDimensionsResult;
