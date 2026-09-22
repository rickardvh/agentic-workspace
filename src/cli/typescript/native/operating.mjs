// Public envelope construction only; Rust owns admission and meaning.
import { request } from "./_transport.mjs";

export function answerCarried(carriage, reference, answer) {
  return request({start: {request: carriage, reference, answer, projection: "carried"}});
}

export function invokeCarried(carriage, reference) {
  return request({invoke: {invocation: carriage, reference, projection: "carried"}});
}

export function selectReference(context, reference, ...answer) {
  if (answer.length > 1) throw new TypeError("selectReference accepts one bounded answer");
  return start({...context, reference, ...(answer.length ? {answer: answer[0]} : {})});
}

export function start(context) {
  return request({start: context});
}

export function resources(context) {
  return request({resources: context});
}

export function invoke(context) {
  return request({invoke: context});
}
