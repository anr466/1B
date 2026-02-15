module.exports = {
  preset: 'react-native',
  setupFilesAfterEnv: ['<rootDir>/jest.setup.js'],
  transformIgnorePatterns: [
    'node_modules/(?!(react-native|@react-native|react-native-vector-icons|react-native-svg|@react-navigation|react-native-linear-gradient|react-native-fs)/)',
  ],
  moduleNameMapper: {
    '\\.(jpg|jpeg|png|gif|eot|otf|webp|svg|ttf|woff|woff2|mp4|webm|wav|mp3|m4a|aac|oga)$':
      'identity-obj-proxy',
  },
  testEnvironment: 'node',
  testTimeout: 30000,
  maxWorkers: 1,
  maxConcurrency: 1,
  forceExit: true,
  clearMocks: true,
  resetMocks: true,
  restoreMocks: true,
  collectCoverageFrom: [
    'src/**/*.{js,jsx}',
    '!src/**/*.test.{js,jsx}',
    '!src/index.js',
  ],
  moduleDirectories: ['node_modules', '<rootDir>/src'],
};
